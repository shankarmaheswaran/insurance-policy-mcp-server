"""
Web GUI for the Insurance Policy MCP Server
"""

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, render_template, request, jsonify

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from store import PolicyStore
from types_import import CreatePolicyInput, SubmitClaimInput

app = Flask(__name__, template_folder="templates", static_folder="static")
store = PolicyStore()
REMOTE_BACKEND_URL = os.getenv("POLICY_BACKEND_URL", "").rstrip("/")


def remote_request(path: str, method: str = "GET", payload: dict | None = None):
    """Forward an API request to a remote backend when the UI runs locally."""
    query_string = request.query_string.decode("utf-8")
    url = f"{REMOTE_BACKEND_URL}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    try:
        backend_request = Request(url, data=body, headers=headers, method=method)
        with urlopen(backend_request, timeout=15) as response:
            response_body = json.loads(response.read().decode("utf-8"))
            return jsonify(response_body), response.status
    except HTTPError as error:
        error_body = error.read().decode("utf-8")
        try:
            response_body = json.loads(error_body)
        except json.JSONDecodeError:
            response_body = {"error": error_body or error.reason}
        return jsonify(response_body), error.code
    except URLError as error:
        return jsonify({"error": f"Remote backend unavailable: {error.reason}"}), 502


@app.route("/")
def index():
    """Home page"""
    return render_template("index.html")


@app.route("/agent")
@app.route("/test")
def policy_agent():
    """Policy Agent page"""
    return render_template("test-console.html")


@app.route("/api/policies", methods=["GET"])
def get_policies():
    """Get all policies"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/policies")

    customer_id = request.args.get("customer_id")
    policies = store.list_policies(customer_id)
    return jsonify([p.__dict__ for p in policies])


@app.route("/api/policies", methods=["POST"])
def create_policy():
    """Create a new policy"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/policies", method="POST", payload=request.json)

    try:
        data = request.json
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
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/policies/<policy_id>", methods=["GET"])
def get_policy(policy_id):
    """Get a specific policy"""
    if REMOTE_BACKEND_URL:
        return remote_request(f"/api/policies/{policy_id}")

    policy = store.get_policy(policy_id)
    if not policy:
        return jsonify({"error": "Policy not found"}), 404
    return jsonify(policy.__dict__)


@app.route("/api/coverage-options", methods=["GET"])
def get_coverage_options():
    """Get available coverage options"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/coverage-options")

    policy_type = request.args.get("policy_type")
    options = store.list_coverage_options(policy_type)
    return jsonify([o.__dict__ for o in options])


@app.route("/api/claims", methods=["GET"])
def get_claims():
    """Get all claims"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/claims")

    policy_id = request.args.get("policy_id")
    claims = store.list_claims(policy_id)
    return jsonify([c.__dict__ for c in claims])


@app.route("/api/claims", methods=["POST"])
def submit_claim():
    """Submit a new claim"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/claims", method="POST", payload=request.json)

    try:
        data = request.json
        input_data = SubmitClaimInput(
            policy_id=data["policy_id"],
            claim_type=data["claim_type"],
            amount=float(data["amount"]),
            description=data["description"],
        )
        claim = store.submit_claim(input_data)
        return jsonify(claim.__dict__), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Get statistics"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/stats")

    policies = store.list_policies()
    claims = store.list_claims()
    return jsonify({
        "total_policies": len(policies),
        "active_policies": len([p for p in policies if p.status == "active"]),
        "total_claims": len(claims),
        "approved_claims": len([c for c in claims if c.status == "approved"]),
        "submitted_claims": len([c for c in claims if c.status == "submitted"]),
    })


@app.route("/api/agent/execute", methods=["POST"])
@app.route("/api/test/execute", methods=["POST"])
def agent_execute_tool():
    """Execute a Policy Agent tool"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/agent/execute", method="POST", payload=request.json)

    try:
        data = request.json
        tool_name = data.get("tool_name")
        tool_params = data.get("params", {})

        # Log the request
        logs = [f"[REQUEST] Tool: {tool_name}"]
        logs.append(f"[PARAMS] {json.dumps(tool_params, indent=2)}")

        # Execute the tool
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
                logs.append(f"[SUCCESS] Policy found")
            else:
                result = None
                logs.append(f"[WARNING] Policy not found: {tool_params['policy_id']}")

        elif tool_name == "list_policies":
            logs.append("[EXECUTING] Listing policies...")
            policies = store.list_policies(tool_params.get("customer_id"))
            result = [p.__dict__ for p in policies]
            logs.append(f"[SUCCESS] Found {len(policies)} policies")

        elif tool_name == "get_coverage_options":
            logs.append("[EXECUTING] Retrieving coverage options...")
            options = store.list_coverage_options(tool_params.get("policy_type"))
            result = [o.__dict__ for o in options]
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
            result = [c.__dict__ for c in claims]
            logs.append(f"[SUCCESS] Found {len(claims)} claims")

        else:
            logs.append(f"[ERROR] Unknown tool: {tool_name}")
            return jsonify({
                "success": False,
                "result": None,
                "logs": logs,
                "error": f"Unknown tool: {tool_name}"
            })

        logs.append("[COMPLETE] Tool execution finished")
        return jsonify({
            "success": True,
            "result": result,
            "logs": logs
        })

    except Exception as e:
        logs = [f"[ERROR] {str(e)}"]
        import traceback
        logs.extend(traceback.format_exc().split("\n"))
        return jsonify({
            "success": False,
            "result": None,
            "logs": logs,
            "error": str(e)
        }), 400


@app.route("/api/agent/tools", methods=["GET"])
@app.route("/api/test/tools", methods=["GET"])
def agent_get_tools():
    """Get available Policy Agent tools"""
    if REMOTE_BACKEND_URL:
        return remote_request("/api/agent/tools")

    tools = [
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
                "coverage_options": "array of strings"
            }
        },
        {
            "name": "get_policy",
            "description": "Get a specific policy",
            "params": {
                "policy_id": "string"
            }
        },
        {
            "name": "list_policies",
            "description": "List all policies",
            "params": {
                "customer_id": "string (optional)"
            }
        },
        {
            "name": "get_coverage_options",
            "description": "Get available coverage options",
            "params": {
                "policy_type": "string (optional)"
            }
        },
        {
            "name": "submit_claim",
            "description": "Submit a claim",
            "params": {
                "policy_id": "string",
                "claim_type": "string",
                "amount": "number",
                "description": "string"
            }
        },
        {
            "name": "list_claims",
            "description": "List all claims",
            "params": {
                "policy_id": "string (optional)"
            }
        }
    ]
    return jsonify(tools)


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
