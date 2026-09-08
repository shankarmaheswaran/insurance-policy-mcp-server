"""
Laptop Policy Agent UI.

This app renders the dashboard and Policy Agent pages locally, then forwards API
requests to the backend hosted on AWS EC2.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder="templates", static_folder="static")
BACKEND_URL = os.getenv("POLICY_BACKEND_URL", "").rstrip("/")


def require_backend_url():
    """Return an error response when the UI is not configured with a backend."""
    if BACKEND_URL:
        return None
    return jsonify(
        {
            "error": "POLICY_BACKEND_URL is not configured. Set it to your EC2 backend URL."
        }
    ), 500


def backend_request(path: str, method: str = "GET", payload: dict | None = None):
    """Forward an API request to the EC2 backend."""
    missing_backend = require_backend_url()
    if missing_backend:
        return missing_backend

    query_string = request.query_string.decode("utf-8")
    url = f"{BACKEND_URL}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    try:
        outbound_request = Request(url, data=body, headers=headers, method=method)
        with urlopen(outbound_request, timeout=15) as response:
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
        return jsonify({"error": f"Backend unavailable: {error.reason}"}), 502


@app.route("/")
def index():
    """Dashboard page."""
    return render_template("index.html")


@app.route("/agent")
@app.route("/test")
def policy_agent():
    """Policy Agent page."""
    return render_template("test-console.html")


@app.route("/health", methods=["GET"])
def health_check():
    """Health check for the local Policy Agent UI."""
    return jsonify({"status": "ok", "service": "policy-agent-ui", "backend_url": BACKEND_URL})


@app.route("/api/policies", methods=["GET"])
def get_policies():
    """Proxy policy list requests."""
    return backend_request("/api/policies")


@app.route("/api/policies", methods=["POST"])
def create_policy():
    """Proxy policy creation requests."""
    return backend_request("/api/policies", method="POST", payload=request.json)


@app.route("/api/policies/<policy_id>", methods=["GET"])
def get_policy(policy_id: str):
    """Proxy single policy requests."""
    return backend_request(f"/api/policies/{policy_id}")


@app.route("/api/coverage-options", methods=["GET"])
def get_coverage_options():
    """Proxy coverage option requests."""
    return backend_request("/api/coverage-options")


@app.route("/api/claims", methods=["GET"])
def get_claims():
    """Proxy claim list requests."""
    return backend_request("/api/claims")


@app.route("/api/claims", methods=["POST"])
def submit_claim():
    """Proxy claim submission requests."""
    return backend_request("/api/claims", method="POST", payload=request.json)


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Proxy dashboard stats requests."""
    return backend_request("/api/stats")


@app.route("/api/agent/execute", methods=["POST"])
@app.route("/api/test/execute", methods=["POST"])
def agent_execute_tool():
    """Proxy Policy Agent action execution."""
    return backend_request("/api/agent/execute", method="POST", payload=request.json)


@app.route("/api/agent/tools", methods=["GET"])
@app.route("/api/test/tools", methods=["GET"])
def agent_get_tools():
    """Proxy Policy Agent capability requests."""
    return backend_request("/api/agent/tools")


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
