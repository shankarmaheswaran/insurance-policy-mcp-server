"""
EC2 backend API for the Insurance Policy MCP project.
"""

import json
import os

from flask import Flask, jsonify, request

from src.store import PolicyStore
from src.types_import import CreatePolicyInput, SubmitClaimInput

app = Flask(__name__)
store = PolicyStore()

AGENT_TOOLS = [
    {
        "name": "create_policy",
        "description": "Create a new insurance policy",
        "allowed_roles": ["supervisor", "admin"],
        "params": {
            "customer_id": "string",
            "policy_type": "auto|home|health|life",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "premium": "number",
            "deductible": "number",
            "policy_limit": "number",
            "coverage_options": "array of strings",
        },
    },
    {
        "name": "get_policy",
        "description": "Get a specific policy",
        "allowed_roles": ["consumer", "supervisor", "admin"],
        "params": {"policy_id": "string"},
    },
    {
        "name": "list_policies",
        "description": "List policies visible to the signed-in role",
        "allowed_roles": ["consumer", "supervisor", "admin"],
        "params": {"customer_id": "string (optional)"},
    },
    {
        "name": "get_coverage_options",
        "description": "Get available coverage options",
        "allowed_roles": ["consumer", "supervisor", "admin"],
        "params": {"policy_type": "string (optional)"},
    },
    {
        "name": "submit_claim",
        "description": "Submit a claim",
        "allowed_roles": ["supervisor", "admin"],
        "params": {
            "policy_id": "string",
            "claim_type": "string",
            "amount": "number",
            "description": "string",
        },
    },
    {
        "name": "list_claims",
        "description": "List claims visible to the signed-in role",
        "allowed_roles": ["consumer", "supervisor", "admin"],
        "params": {"policy_id": "string (optional)"},
    },
    {
        "name": "update_policy",
        "description": "Edit allowed policy fields for a consumer policy",
        "allowed_roles": ["supervisor", "admin"],
        "params": {
            "policy_id": "string",
            "premium": "number (optional)",
            "deductible": "number (optional)",
            "policy_limit": "number (optional)",
            "coverage_options": "array of strings (optional)",
            "start_date": "YYYY-MM-DD (optional)",
            "end_date": "YYYY-MM-DD (optional)",
        },
    },
    {
        "name": "renew_policy",
        "description": "Renew a policy by extending its end date",
        "allowed_roles": ["supervisor", "admin"],
        "params": {
            "policy_id": "string",
            "end_date": "YYYY-MM-DD",
            "premium": "number (optional)",
        },
    },
    {
        "name": "change_policy_status",
        "description": "Change a policy status without deleting it",
        "allowed_roles": ["supervisor", "admin"],
        "params": {"policy_id": "string", "status": "active|inactive|cancelled"},
    },
    {
        "name": "get_policy_holder",
        "description": "Get a policy holder profile visible to the signed-in role",
        "allowed_roles": ["consumer", "supervisor", "admin"],
        "params": {"customer_id": "string"},
    },
    {
        "name": "list_policy_holders",
        "description": "List policy holder profiles visible to the signed-in role",
        "allowed_roles": ["consumer", "supervisor", "admin"],
        "params": {},
    },
    {
        "name": "list_agent_logins",
        "description": "List demo Policy Agent login accounts",
        "allowed_roles": ["admin"],
        "params": {"role": "consumer|supervisor|admin (optional)"},
    },
]

ROLE_PERMISSIONS = {
    "consumer": {
        "get_policy",
        "list_policies",
        "get_coverage_options",
        "list_claims",
        "get_policy_holder",
        "list_policy_holders",
    },
    "supervisor": {
        "get_policy",
        "list_policies",
        "get_coverage_options",
        "submit_claim",
        "list_claims",
        "create_policy",
        "update_policy",
        "renew_policy",
        "change_policy_status",
        "get_policy_holder",
        "list_policy_holders",
    },
    "admin": {tool["name"] for tool in AGENT_TOOLS},
}


def get_agent_context() -> tuple[str | None, str | None]:
    """Read the role context sent by the laptop Policy Agent UI."""
    role_header = request.headers.get("X-Policy-Agent-Role")
    username = request.headers.get("X-Policy-Agent-Username")
    customer_id = request.headers.get("X-Policy-Agent-Customer-Id")
    if not role_header or not username:
        return None, customer_id

    role = role_header.lower()
    if role not in ROLE_PERMISSIONS:
        return None, customer_id

    login = store.agent_logins.get(username)
    if not login or login.role != role:
        return None, customer_id
    customer_id = login.customer_id or customer_id
    return role, customer_id


def get_tools_for_role(role: str) -> list[dict]:
    """Return only the MCP actions available to a role."""
    allowed_tools = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["consumer"])
    return [tool for tool in AGENT_TOOLS if tool["name"] in allowed_tools]


def serialize_login(login) -> dict:
    """Serialize demo login accounts for API responses."""
    return {
        "username": login.username,
        "role": login.role,
        "display_name": login.display_name,
        "customer_id": login.customer_id,
    }


def serialize_public_login(login) -> dict:
    """Serialize non-sensitive login choices for the signed-out UI."""
    return {
        "username": login.username,
        "role": login.role,
        "display_name": login.display_name,
    }


def serialize_personal_info(profile) -> dict:
    """Serialize mock personal information for demo UI responses."""
    return {
        "username": profile.username,
        "role": profile.role,
        "name": profile.name,
        "phone_number": profile.phone_number,
        "address": profile.address,
        "ssn": profile.ssn,
        "passport_number": profile.passport_number,
        "annual_income": profile.annual_income,
        "family_members": profile.family_members,
        "customer_id": profile.customer_id,
    }


def error_result(message: str, logs: list[str], status_code: int = 403):
    """Return a consistent Policy Agent error response."""
    logs.append(f"[ERROR] {message}")
    return jsonify({"success": False, "result": None, "logs": logs, "error": message}), status_code


@app.route("/health", methods=["GET"])
def health_check():
    """Health check for load balancers and deployment validation."""
    return jsonify({"status": "ok", "service": "policy-mcp-backend"})


@app.route("/api/policies", methods=["GET"])
def get_policies():
    """Get all policies."""
    customer_id = request.args.get("customer_id")
    policies = store.list_policies(customer_id)
    return jsonify([policy.__dict__ for policy in policies])


@app.route("/api/policies", methods=["POST"])
def create_policy():
    """Create a new policy."""
    try:
        data = request.json or {}
        if not store.get_policy_holder(data["customer_id"]):
            return jsonify({"error": f"Customer not found: {data['customer_id']}"}), 400
        input_data = CreatePolicyInput(
            customer_id=data["customer_id"],
            policy_type=data["policy_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            premium=float(data["premium"]),
            coverage_options=data.get("coverage_options", []),
            deductible=float(data["deductible"]),
            policy_limit=float(data["policy_limit"]),
        )
        policy = store.create_policy(input_data)
        return jsonify(policy.__dict__), 201
    except Exception as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/policies/<policy_id>", methods=["GET"])
def get_policy(policy_id: str):
    """Get a specific policy."""
    policy = store.get_policy(policy_id)
    if not policy:
        return jsonify({"error": "Policy not found"}), 404
    return jsonify(policy.__dict__)


@app.route("/api/coverage-options", methods=["GET"])
def get_coverage_options():
    """Get available coverage options."""
    policy_type = request.args.get("policy_type")
    options = store.list_coverage_options(policy_type)
    return jsonify([option.__dict__ for option in options])


@app.route("/api/claims", methods=["GET"])
def get_claims():
    """Get all claims."""
    policy_id = request.args.get("policy_id")
    claims = store.list_claims(policy_id)
    return jsonify([claim.__dict__ for claim in claims])


@app.route("/api/claims", methods=["POST"])
def submit_claim():
    """Submit a new claim."""
    try:
        data = request.json or {}
        input_data = SubmitClaimInput(
            policy_id=data["policy_id"],
            claim_type=data["claim_type"],
            amount=float(data["amount"]),
            description=data["description"],
        )
        claim = store.submit_claim(input_data)
        return jsonify(claim.__dict__), 201
    except Exception as error:
        return jsonify({"error": str(error)}), 400


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get dashboard statistics."""
    policies = store.list_policies()
    claims = store.list_claims()
    return jsonify(
        {
            "total_policies": len(policies),
            "active_policies": len([policy for policy in policies if policy.status == "active"]),
            "total_claims": len(claims),
            "approved_claims": len([claim for claim in claims if claim.status == "approved"]),
            "submitted_claims": len([claim for claim in claims if claim.status == "submitted"]),
        }
    )


@app.route("/api/agent/execute", methods=["POST"])
def agent_execute_tool():
    """Execute a Policy Agent action."""
    logs: list[str] = []
    try:
        role, customer_id = get_agent_context()
        if role is None:
            return error_result("Login role is required before running Policy Agent actions", logs, 401)

        data = request.json or {}
        tool_name = data.get("tool_name")
        tool_params = data.get("params", {})

        logs = [f"[REQUEST] Tool: {tool_name}"]
        logs.append(f"[AUTH] Role: {role}")
        if customer_id:
            logs.append(f"[AUTH] Customer scope: {customer_id}")
        logs.append(f"[PARAMS] {json.dumps(tool_params, indent=2)}")

        if tool_name not in ROLE_PERMISSIONS[role]:
            return error_result(f"Role '{role}' is not allowed to run '{tool_name}'", logs)

        result = None
        if tool_name == "create_policy":
            logs.append("[EXECUTING] Creating new policy...")
            if not store.get_policy_holder(tool_params["customer_id"]):
                return error_result(f"Customer not found: {tool_params['customer_id']}", logs, 400)
            input_data = CreatePolicyInput(
                customer_id=tool_params["customer_id"],
                policy_type=tool_params["policy_type"],
                start_date=tool_params["start_date"],
                end_date=tool_params["end_date"],
                premium=float(tool_params["premium"]),
                coverage_options=tool_params.get("coverage_options", []),
                deductible=float(tool_params["deductible"]),
                policy_limit=float(tool_params["policy_limit"]),
            )
            policy = store.create_policy(input_data)
            result = policy.__dict__
            logs.append(f"[SUCCESS] Policy created with ID: {policy.id}")

        elif tool_name == "get_policy":
            logs.append("[EXECUTING] Retrieving policy...")
            policy = store.get_policy(tool_params["policy_id"])
            if policy:
                if role == "consumer" and policy.customer_id != customer_id:
                    return error_result("Consumer role can only access its own policies", logs)
                result = policy.__dict__
                logs.append("[SUCCESS] Policy found")
            else:
                logs.append(f"[WARNING] Policy not found: {tool_params['policy_id']}")

        elif tool_name == "list_policies":
            logs.append("[EXECUTING] Listing policies...")
            filter_customer_id = tool_params.get("customer_id")
            if role == "consumer":
                if not customer_id:
                    return error_result("Consumer role requires a customer ID scope", logs)
                if filter_customer_id and filter_customer_id != customer_id:
                    return error_result("Consumer role cannot list another customer's policies", logs)
                filter_customer_id = customer_id
                logs.append(f"[AUTH] Consumer policy list scoped to {customer_id}")
            policies = store.list_policies(filter_customer_id)
            result = [policy.__dict__ for policy in policies]
            logs.append(f"[SUCCESS] Found {len(policies)} policies")

        elif tool_name == "get_coverage_options":
            logs.append("[EXECUTING] Retrieving coverage options...")
            options = store.list_coverage_options(tool_params.get("policy_type"))
            result = [option.__dict__ for option in options]
            logs.append(f"[SUCCESS] Found {len(options)} coverage options")

        elif tool_name == "submit_claim":
            logs.append("[EXECUTING] Submitting claim...")
            policy = store.get_policy(tool_params["policy_id"])
            if not policy:
                return error_result(f"Policy not found: {tool_params['policy_id']}", logs, 404)
            if role == "consumer" and policy.customer_id != customer_id:
                return error_result("Consumer role can only submit claims for its own policies", logs)
            input_data = SubmitClaimInput(
                policy_id=tool_params["policy_id"],
                claim_type=tool_params["claim_type"],
                amount=float(tool_params["amount"]),
                description=tool_params["description"],
            )
            claim = store.submit_claim(input_data)
            result = claim.__dict__
            logs.append(f"[SUCCESS] Claim submitted with ID: {claim.id}")

        elif tool_name == "update_policy":
            logs.append("[EXECUTING] Updating policy...")
            editable_updates = {}
            for field_name in (
                "policy_type",
                "start_date",
                "end_date",
                "premium",
                "coverage_options",
                "deductible",
                "policy_limit",
            ):
                if field_name in tool_params and tool_params[field_name] not in ("", None):
                    editable_updates[field_name] = tool_params[field_name]
            for number_field in ("premium", "deductible", "policy_limit"):
                if number_field in editable_updates:
                    editable_updates[number_field] = float(editable_updates[number_field])

            policy = store.update_policy(tool_params["policy_id"], editable_updates)
            if not policy:
                return error_result(f"Policy not found: {tool_params['policy_id']}", logs, 404)
            result = policy.__dict__
            logs.append(f"[SUCCESS] Policy updated: {policy.id}")

        elif tool_name == "renew_policy":
            logs.append("[EXECUTING] Renewing policy...")
            premium = tool_params.get("premium")
            policy = store.renew_policy(
                tool_params["policy_id"],
                tool_params["end_date"],
                float(premium) if premium not in (None, "") else None,
            )
            if not policy:
                return error_result(f"Policy not found: {tool_params['policy_id']}", logs, 404)
            result = policy.__dict__
            logs.append(f"[SUCCESS] Policy renewed through {policy.end_date}")

        elif tool_name == "change_policy_status":
            logs.append("[EXECUTING] Changing policy status...")
            policy = store.change_policy_status(tool_params["policy_id"], tool_params["status"])
            if not policy:
                return error_result(f"Policy not found: {tool_params['policy_id']}", logs, 404)
            result = policy.__dict__
            logs.append(f"[SUCCESS] Policy status changed to {policy.status}")

        elif tool_name == "list_claims":
            logs.append("[EXECUTING] Listing claims...")
            filter_policy_id = tool_params.get("policy_id")
            if role == "consumer":
                if not customer_id:
                    return error_result("Consumer role requires a customer ID scope", logs)
                allowed_policy_ids = {
                    policy.id for policy in store.list_policies(customer_id)
                }
                if filter_policy_id and filter_policy_id not in allowed_policy_ids:
                    return error_result("Consumer role cannot list claims for another policy", logs)
                claims = [
                    claim
                    for claim in store.list_claims(filter_policy_id)
                    if claim.policy_id in allowed_policy_ids
                ]
                logs.append(f"[AUTH] Consumer claims list scoped to {customer_id}")
            else:
                claims = store.list_claims(filter_policy_id)
            result = [claim.__dict__ for claim in claims]
            logs.append(f"[SUCCESS] Found {len(claims)} claims")

        elif tool_name == "get_policy_holder":
            logs.append("[EXECUTING] Retrieving policy holder profile...")
            requested_customer_id = tool_params["customer_id"]
            if role == "consumer" and requested_customer_id != customer_id:
                return error_result("Consumer role can only access its own profile", logs)
            holder = store.get_policy_holder(requested_customer_id)
            if holder:
                result = holder.__dict__
                logs.append("[SUCCESS] Policy holder profile found")
            else:
                logs.append(f"[WARNING] Policy holder not found: {requested_customer_id}")

        elif tool_name == "list_policy_holders":
            logs.append("[EXECUTING] Listing policy holder profiles...")
            if role == "consumer":
                if not customer_id:
                    return error_result("Consumer role requires a customer ID scope", logs)
                holder = store.get_policy_holder(customer_id)
                holders = [holder] if holder else []
                logs.append(f"[AUTH] Consumer holder list scoped to {customer_id}")
            else:
                holders = store.list_policy_holders()
            result = [holder.__dict__ for holder in holders]
            logs.append(f"[SUCCESS] Found {len(holders)} policy holder profiles")

        elif tool_name == "list_agent_logins":
            logs.append("[EXECUTING] Listing demo agent logins...")
            logins = store.list_agent_logins(tool_params.get("role"))
            result = [serialize_login(login) for login in logins]
            logs.append(f"[SUCCESS] Found {len(logins)} demo login accounts")

        else:
            logs.append(f"[ERROR] Unknown tool: {tool_name}")
            return jsonify(
                {
                    "success": False,
                    "result": None,
                    "logs": logs,
                    "error": f"Unknown tool: {tool_name}",
                }
            )

        logs.append("[COMPLETE] Tool execution finished")
        return jsonify({"success": True, "result": result, "logs": logs})

    except Exception as error:
        logs.append(f"[ERROR] {str(error)}")
        return jsonify({"success": False, "result": None, "logs": logs, "error": str(error)}), 400


@app.route("/api/agent/tools", methods=["GET"])
def agent_get_tools():
    """Get available Policy Agent actions."""
    role, _ = get_agent_context()
    if role is None:
        return jsonify({"error": "Login role is required before viewing MCP actions"}), 401

    return jsonify(get_tools_for_role(role))


@app.route("/api/agent/logins", methods=["GET"])
def agent_get_logins():
    """Get demo Policy Agent login accounts for the UI."""
    role = request.args.get("role")
    return jsonify([serialize_public_login(login) for login in store.list_agent_logins(role)])


@app.route("/api/agent/personal-info", methods=["GET"])
def agent_get_personal_info():
    """Get mock personal information visible to the signed-in role."""
    role, _ = get_agent_context()
    username = request.headers.get("X-Policy-Agent-Username")
    if role is None or not username:
        return jsonify({"error": "Login is required before viewing personal information"}), 401

    if role == "consumer":
        profile = store.get_agent_personal_info(username)
        return jsonify(
            {
                "mock_data_notice": "All SSN and passport values are fake demo identifiers.",
                "consumers": [serialize_personal_info(profile)] if profile else [],
                "supervisors": [],
            }
        )

    if role == "supervisor":
        profile = store.get_agent_personal_info(username)
        return jsonify(
            {
                "mock_data_notice": "All SSN and passport values are fake demo identifiers.",
                "consumers": [
                    serialize_personal_info(profile)
                    for profile in store.list_agent_personal_info("consumer")
                ],
                "supervisors": [serialize_personal_info(profile)] if profile else [],
            }
        )

    return jsonify(
        {
            "mock_data_notice": "All SSN and passport values are fake demo identifiers.",
            "consumers": [
                serialize_personal_info(profile)
                for profile in store.list_agent_personal_info("consumer")
            ],
            "supervisors": [
                serialize_personal_info(profile)
                for profile in store.list_agent_personal_info("supervisor")
            ],
        }
    )


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
