"""
Laptop Policy Agent UI.

This app renders the dashboard and Policy Agent pages locally, then forwards API
requests to the backend hosted on AWS EC2.
"""

import json
import os
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder="templates", static_folder="static")
BACKEND_URL = os.getenv("POLICY_BACKEND_URL", "").rstrip("/")
MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "https://mcp-aigw.portkey.ai").rstrip("/")
MCP_GATEWAY_CONFIG_FILE = os.getenv("MCP_GATEWAY_CONFIG_FILE", "")
MCP_GATEWAY_TEST_PATH = os.getenv("MCP_GATEWAY_TEST_PATH", "/")
MCP_GATEWAY_VERIFY_SSL = os.getenv("MCP_GATEWAY_VERIFY_SSL", "1") != "0"


def require_backend_url():
    """Return an error response when the UI is not configured with a backend."""
    if BACKEND_URL:
        return None
    return jsonify(
        {
            "error": "POLICY_BACKEND_URL is not configured. Set it to your EC2 backend URL."
        }
    ), 500


def load_gateway_headers() -> tuple[dict[str, str], list[str], list[str]]:
    """Load MCP gateway headers from env/YAML without exposing secret values."""
    headers: dict[str, str] = {"Accept": "application/json"}
    header_names: list[str] = []
    logs: list[str] = []

    headers_json = os.getenv("MCP_GATEWAY_HEADERS_JSON")
    if headers_json:
        try:
            parsed_headers = json.loads(headers_json)
            for name, value in parsed_headers.items():
                if value:
                    headers[str(name)] = str(value)
                    header_names.append(str(name))
            logs.append("[CONFIG] Loaded MCP gateway headers from MCP_GATEWAY_HEADERS_JSON")
        except json.JSONDecodeError:
            logs.append("[WARNING] MCP_GATEWAY_HEADERS_JSON is not valid JSON")

    auth_name = os.getenv("MCP_GATEWAY_AUTH_HEADER_NAME")
    auth_value = os.getenv("MCP_GATEWAY_AUTH_HEADER_VALUE")
    if auth_name and auth_value:
        headers[auth_name] = auth_value
        header_names.append(auth_name)
        logs.append("[CONFIG] Loaded MCP gateway auth header from environment")

    if MCP_GATEWAY_CONFIG_FILE:
        try:
            import yaml
        except ImportError:
            logs.append("[WARNING] PyYAML is not installed; YAML gateway config was not loaded")
        else:
            try:
                with open(MCP_GATEWAY_CONFIG_FILE, "r", encoding="utf-8") as config_file:
                    config = yaml.safe_load(config_file) or {}
                yaml_headers = config.get("headers", {}) if isinstance(config, dict) else {}
                if isinstance(yaml_headers, dict):
                    for name, value in yaml_headers.items():
                        if value:
                            headers[str(name)] = str(value)
                            header_names.append(str(name))
                for key in ("api_key", "portkey_api_key", "virtual_key", "bearer_token"):
                    value = config.get(key) if isinstance(config, dict) else None
                    if value and key not in header_names:
                        header_name = "Authorization" if key == "bearer_token" else f"X-{key.replace('_', '-')}"
                        header_value = f"Bearer {value}" if key == "bearer_token" else str(value)
                        headers[header_name] = header_value
                        header_names.append(header_name)
                environment_data = config.get("environment", {}).get("data", {}) if isinstance(config, dict) else {}
                client_auth = environment_data.get("PORTKEY_CLIENT_AUTH") if isinstance(environment_data, dict) else None
                if client_auth:
                    auth_header_name = os.getenv("MCP_GATEWAY_YAML_AUTH_HEADER", "Authorization")
                    auth_header_value = (
                        str(client_auth)
                        if auth_header_name.lower() != "authorization"
                        else f"Bearer {client_auth}"
                    )
                    headers[auth_header_name] = auth_header_value
                    header_names.append(auth_header_name)
                logs.append("[CONFIG] Loaded MCP gateway YAML config file")
            except OSError as error:
                logs.append(f"[WARNING] Could not read MCP gateway YAML config file: {error.strerror}")

    return headers, sorted(set(header_names)), logs


def check_mcp_gateway() -> dict:
    """Check the configured MCP gateway URL without logging secrets."""
    gateway_url = f"{MCP_GATEWAY_URL}{MCP_GATEWAY_TEST_PATH}"
    gateway_host = urlparse(MCP_GATEWAY_URL).hostname or MCP_GATEWAY_URL
    headers, header_names, logs = load_gateway_headers()
    logs.insert(0, f"[CONFIG] MCP Gateway URL: {MCP_GATEWAY_URL}")
    logs.append(f"[CONFIG] MCP Gateway host: {gateway_host}")
    logs.append(f"[CONFIG] Credential headers configured: {', '.join(header_names) if header_names else 'none'}")
    logs.append(f"[CONFIG] TLS certificate verification: {'enabled' if MCP_GATEWAY_VERIFY_SSL else 'disabled for local test'}")
    logs.append(f"[CHECK] Calling MCP gateway test endpoint: {gateway_url}")

    try:
        gateway_request = Request(gateway_url, headers=headers, method="GET")
        ssl_context = None if MCP_GATEWAY_VERIFY_SSL else ssl._create_unverified_context()
        with urlopen(gateway_request, timeout=15, context=ssl_context) as response:
            logs.append(f"[SUCCESS] MCP gateway returned HTTP {response.status}")
            return {
                "configured": True,
                "connected": 200 <= response.status < 300,
                "reachable": True,
                "url": MCP_GATEWAY_URL,
                "host": gateway_host,
                "status_code": response.status,
                "headers_configured": bool(header_names),
                "header_names": header_names,
                "logs": logs,
            }
    except HTTPError as error:
        logs.append(f"[WARNING] MCP gateway reached but returned HTTP {error.code}: {error.reason}")
        return {
            "configured": True,
            "connected": False,
            "reachable": True,
            "url": MCP_GATEWAY_URL,
            "host": gateway_host,
            "status_code": error.code,
            "headers_configured": bool(header_names),
            "header_names": header_names,
            "logs": logs,
            "error": error.reason,
        }
    except URLError as error:
        logs.append(f"[ERROR] MCP gateway unavailable: {error.reason}")
        return {
            "configured": True,
            "connected": False,
            "reachable": False,
            "url": MCP_GATEWAY_URL,
            "host": gateway_host,
            "headers_configured": bool(header_names),
            "header_names": header_names,
            "logs": logs,
            "error": str(error.reason),
        }


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
    agent_role = request.headers.get("X-Policy-Agent-Role")
    agent_username = request.headers.get("X-Policy-Agent-Username")
    agent_customer_id = request.headers.get("X-Policy-Agent-Customer-Id")
    if agent_role:
        headers["X-Policy-Agent-Role"] = agent_role
    if agent_username:
        headers["X-Policy-Agent-Username"] = agent_username
    if agent_customer_id:
        headers["X-Policy-Agent-Customer-Id"] = agent_customer_id
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
    return jsonify(
        {
            "status": "ok",
            "service": "policy-agent-ui",
            "backend_url": BACKEND_URL,
            "mcp_gateway_url": MCP_GATEWAY_URL,
        }
    )


@app.route("/api/agent/connection", methods=["GET"])
def agent_connection_check():
    """Verify that the Policy Agent UI is connected to the remote backend."""
    agent_role = request.headers.get("X-Policy-Agent-Role")
    agent_username = request.headers.get("X-Policy-Agent-Username")
    if not agent_role or not agent_username:
        return jsonify({"error": "Login is required before viewing MCP connection details"}), 401

    missing_backend = require_backend_url()
    if missing_backend:
        return missing_backend

    backend_host = urlparse(BACKEND_URL).hostname or BACKEND_URL
    agent_customer_id = request.headers.get("X-Policy-Agent-Customer-Id")
    logs = [
        f"[CONFIG] Local Policy Agent backend URL: {BACKEND_URL}",
        f"[CONFIG] Remote backend host/IP: {backend_host}",
        f"[AUTH] Agent role: {agent_role}",
        "[CHECK] Calling remote backend /health endpoint...",
    ]
    if agent_username:
        logs.append(f"[AUTH] Agent login: {agent_username}")
    if agent_customer_id:
        logs.append(f"[AUTH] Customer scope: {agent_customer_id}")

    try:
        with urlopen(f"{BACKEND_URL}/health", timeout=10) as health_response:
            health = json.loads(health_response.read().decode("utf-8"))
            logs.append(f"[SUCCESS] Remote health check returned HTTP {health_response.status}")

        logs.append("[CHECK] Calling remote backend /api/agent/tools endpoint...")
        tools_request = Request(
            f"{BACKEND_URL}/api/agent/tools",
            headers={
                "Accept": "application/json",
                "X-Policy-Agent-Role": agent_role,
                "X-Policy-Agent-Username": agent_username or "",
                "X-Policy-Agent-Customer-Id": agent_customer_id or "",
            },
        )
        with urlopen(tools_request, timeout=10) as tools_response:
            tools = json.loads(tools_response.read().decode("utf-8"))
            logs.append(
                f"[SUCCESS] Remote MCP tool API returned {len(tools)} actions for {agent_role}"
            )

        gateway = check_mcp_gateway()
        logs.extend(gateway["logs"])

        logs.append("[COMPLETE] Connected to the configured remote MCP backend")
        return jsonify(
            {
                "connected": True,
                "backend_url": BACKEND_URL,
                "backend_host": backend_host,
                "mcp_gateway": gateway,
                "health": health,
                "tool_count": len(tools),
                "role": agent_role,
                "customer_id": agent_customer_id,
                "logs": logs,
            }
        )
    except HTTPError as error:
        logs.append(f"[ERROR] Remote backend returned HTTP {error.code}: {error.reason}")
        return jsonify(
            {
                "connected": False,
                "backend_url": BACKEND_URL,
                "backend_host": backend_host,
                "logs": logs,
                "error": error.reason,
            }
        ), 502
    except URLError as error:
        logs.append(f"[ERROR] Remote backend unavailable: {error.reason}")
        return jsonify(
            {
                "connected": False,
                "backend_url": BACKEND_URL,
                "backend_host": backend_host,
                "logs": logs,
                "error": str(error.reason),
            }
        ), 502


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


@app.route("/api/agent/logins", methods=["GET"])
def agent_get_logins():
    """Proxy demo Policy Agent login account requests."""
    return backend_request("/api/agent/logins")


@app.route("/api/agent/personal-info", methods=["GET"])
def agent_get_personal_info():
    """Proxy role-scoped mock personal information requests."""
    return backend_request("/api/agent/personal-info")


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
