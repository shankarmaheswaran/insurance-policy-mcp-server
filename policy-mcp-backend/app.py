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
        data = request.json or {}
        tool_name = data.get("tool_name")
        tool_params = data.get("params", {})

        logs = [f"[REQUEST] Tool: {tool_name}"]
        logs.append(f"[PARAMS] {json.dumps(tool_params, indent=2)}")

        result = None
        if tool_name == "create_policy":
            logs.append("[EXECUTING] Creating new policy...")
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
                result = policy.__dict__
                logs.append("[SUCCESS] Policy found")
            else:
                logs.append(f"[WARNING] Policy not found: {tool_params['policy_id']}")

        elif tool_name == "list_policies":
            logs.append("[EXECUTING] Listing policies...")
            policies = store.list_policies(tool_params.get("customer_id"))
            result = [policy.__dict__ for policy in policies]
            logs.append(f"[SUCCESS] Found {len(policies)} policies")

        elif tool_name == "get_coverage_options":
            logs.append("[EXECUTING] Retrieving coverage options...")
            options = store.list_coverage_options(tool_params.get("policy_type"))
            result = [option.__dict__ for option in options]
            logs.append(f"[SUCCESS] Found {len(options)} coverage options")

        elif tool_name == "submit_claim":
            logs.append("[EXECUTING] Submitting claim...")
            input_data = SubmitClaimInput(
                policy_id=tool_params["policy_id"],
                claim_type=tool_params["claim_type"],
                amount=float(tool_params["amount"]),
                description=tool_params["description"],
            )
            claim = store.submit_claim(input_data)
            result = claim.__dict__
            logs.append(f"[SUCCESS] Claim submitted with ID: {claim.id}")

        elif tool_name == "list_claims":
            logs.append("[EXECUTING] Listing claims...")
            claims = store.list_claims(tool_params.get("policy_id"))
            result = [claim.__dict__ for claim in claims]
            logs.append(f"[SUCCESS] Found {len(claims)} claims")

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
    return jsonify(
        [
            {
                "name": "create_policy",
                "description": "Create a new insurance policy",
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
                "params": {"policy_id": "string"},
            },
            {
                "name": "list_policies",
                "description": "List all policies",
                "params": {"customer_id": "string (optional)"},
            },
            {
                "name": "get_coverage_options",
                "description": "Get available coverage options",
                "params": {"policy_type": "string (optional)"},
            },
            {
                "name": "submit_claim",
                "description": "Submit a claim",
                "params": {
                    "policy_id": "string",
                    "claim_type": "string",
                    "amount": "number",
                    "description": "string",
                },
            },
            {
                "name": "list_claims",
                "description": "List all claims",
                "params": {"policy_id": "string (optional)"},
            },
        ]
    )


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
