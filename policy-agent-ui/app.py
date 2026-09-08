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
MCP_GATEWAY_URL = os.getenv(
    "MCP_GATEWAY_URL", "https://mcp-aigw.portkey.ai/insurance-mcp/mcp"
).rstrip("/")
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


def get_connection_mode() -> str:
    """Return the selected backend route mode from the agent UI."""
    mode = request.headers.get("X-Policy-Connection-Mode", "direct").lower()
    return "mcp_gateway" if mode == "mcp_gateway" else "direct"


def get_target_url() -> tuple[str, str]:
    """Return selected route mode and base URL."""
    mode = get_connection_mode()
    return mode, MCP_GATEWAY_URL if mode == "mcp_gateway" else BACKEND_URL


def require_target_url(base_url: str, mode: str):
    """Return an error response if the selected route is not configured."""
    if base_url:
        return None
    setting_name = "MCP_GATEWAY_URL" if mode == "mcp_gateway" else "POLICY_BACKEND_URL"
    return jsonify({"error": f"{setting_name} is not configured for {mode} mode."}), 500


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


def read_gateway_json(response) -> dict:
    """Read JSON or simple SSE data JSON from an MCP gateway response."""
    response_text = response.read().decode("utf-8")
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        for line in response_text.splitlines():
            if line.startswith("data:"):
                data = line.removeprefix("data:").strip()
                if data and data != "[DONE]":
                    return json.loads(data)
        raise


def mcp_gateway_rpc(method: str, params: dict | None = None) -> tuple[dict, int, list[str]]:
    """Call the configured MCP gateway using MCP JSON-RPC over HTTP."""
    headers, header_names, logs = load_gateway_headers()
    headers.update(
        {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
    )
    logs.append(f"[CONFIG] MCP Gateway URL: {MCP_GATEWAY_URL}")
    logs.append(f"[CONFIG] Credential headers configured: {', '.join(header_names) if header_names else 'none'}")
    logs.append(f"[MCP] JSON-RPC method: {method}")

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
    ).encode("utf-8")
    ssl_context = None if MCP_GATEWAY_VERIFY_SSL else ssl._create_unverified_context()

    try:
        gateway_request = Request(MCP_GATEWAY_URL, data=body, headers=headers, method="POST")
        with urlopen(gateway_request, timeout=15, context=ssl_context) as response:
            payload = read_gateway_json(response)
            logs.append(f"[SUCCESS] MCP gateway returned HTTP {response.status}")
            return payload, response.status, logs
    except HTTPError as error:
        error_body = error.read().decode("utf-8")
        logs.append(f"[ERROR] MCP gateway returned HTTP {error.code}: {error.reason}")
        return {
            "error": error.reason,
            "body": error_body,
        }, error.code, logs
    except (URLError, json.JSONDecodeError) as error:
        logs.append(f"[ERROR] MCP gateway request failed: {error}")
        return {"error": str(error)}, 502, logs


def normalize_mcp_tools(payload: dict) -> list[dict]:
    """Convert an MCP tools/list response to the UI's tool-list shape."""
    tools = payload.get("result", {}).get("tools", []) if isinstance(payload, dict) else []
    normalized = []
    for tool in tools:
        input_schema = tool.get("inputSchema", {})
        properties = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
        params = {name: details.get("type", "value") for name, details in properties.items()}
        normalized.append(
            {
                "name": tool.get("name", "unknown"),
                "description": tool.get("description", "MCP gateway tool"),
                "params": params,
            }
        )
    return normalized


def normalize_mcp_tool_result(payload: dict, logs: list[str]) -> dict:
    """Convert an MCP tools/call response to the UI's action result shape."""
    if "error" in payload:
        return {"success": False, "result": None, "logs": logs, "error": payload["error"]}

    result = payload.get("result", {}) if isinstance(payload, dict) else {}
    content = result.get("content", []) if isinstance(result, dict) else []
    parsed_result = result
    if content and isinstance(content, list):
        text = content[0].get("text") if isinstance(content[0], dict) else None
        if text:
            try:
                parsed_result = json.loads(text)
            except json.JSONDecodeError:
                parsed_result = text

    return {
        "success": not result.get("isError", False) if isinstance(result, dict) else True,
        "result": parsed_result,
        "logs": logs,
    }


def mcp_gateway_proxy(path: str, payload: dict | None = None):
    """Proxy supported UI API calls to the MCP gateway protocol."""
    if path == "/api/agent/tools":
        rpc_payload, status, logs = mcp_gateway_rpc("tools/list")
        if status >= 400:
            return jsonify({"error": rpc_payload.get("error"), "logs": logs}), status
        return jsonify(normalize_mcp_tools(rpc_payload)), status

    if path == "/api/agent/execute":
        payload = payload or {}
        rpc_payload, status, logs = mcp_gateway_rpc(
            "tools/call",
            {
                "name": payload.get("tool_name"),
                "arguments": payload.get("params", {}),
            },
        )
        normalized = normalize_mcp_tool_result(rpc_payload, logs)
        return jsonify(normalized), status

    return jsonify({"error": f"MCP Gateway mode does not support REST path {path}"}), 400


def backend_request(path: str, method: str = "GET", payload: dict | None = None):
    """Forward an API request through the selected Direct or MCP Gateway route."""
    mode, base_url = get_target_url()
    missing_target = require_target_url(base_url, mode)
    if missing_target:
        return missing_target

    if mode == "mcp_gateway":
        return mcp_gateway_proxy(path, payload)

    query_string = request.query_string.decode("utf-8")
    url = f"{base_url}{path}"
    if query_string:
        url = f"{url}?{query_string}"

    body = None
    headers = {"Accept": "application/json"}
    gateway_logs: list[str] = []
    if mode == "mcp_gateway":
        headers, _, gateway_logs = load_gateway_headers()
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
        ssl_context = None
        if mode == "mcp_gateway" and not MCP_GATEWAY_VERIFY_SSL:
            ssl_context = ssl._create_unverified_context()
        with urlopen(outbound_request, timeout=15, context=ssl_context) as response:
            response_body = json.loads(response.read().decode("utf-8"))
            return jsonify(response_body), response.status
    except HTTPError as error:
        error_body = error.read().decode("utf-8")
        try:
            response_body = json.loads(error_body)
        except json.JSONDecodeError:
            response_body = {"error": error_body or error.reason}
        if mode == "mcp_gateway" and isinstance(response_body, dict):
            response_body.setdefault("route_mode", mode)
            response_body.setdefault("route_url", base_url)
            response_body.setdefault("gateway_logs", gateway_logs)
        return jsonify(response_body), error.code
    except URLError as error:
        route_name = "MCP gateway" if mode == "mcp_gateway" else "Backend"
        return jsonify(
            {
                "error": f"{route_name} unavailable: {error.reason}",
                "route_mode": mode,
                "route_url": base_url,
                "gateway_logs": gateway_logs,
            }
        ), 502


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
    """Verify that the Policy Agent UI is connected through the selected route."""
    agent_role = request.headers.get("X-Policy-Agent-Role")
    agent_username = request.headers.get("X-Policy-Agent-Username")
    if not agent_role or not agent_username:
        return jsonify({"error": "Login is required before viewing MCP connection details"}), 401

    mode, base_url = get_target_url()
    missing_target = require_target_url(base_url, mode)
    if missing_target:
        return missing_target

    backend_host = urlparse(base_url).hostname or base_url
    agent_customer_id = request.headers.get("X-Policy-Agent-Customer-Id")
    route_label = "MCP Gateway" if mode == "mcp_gateway" else "Direct EC2"
    logs = [
        f"[CONFIG] Selected route: {route_label}",
        f"[CONFIG] Selected route URL: {base_url}",
        f"[CONFIG] Selected route host/IP: {backend_host}",
        f"[AUTH] Local UI login role: {agent_role}",
    ]
    if agent_username:
        logs.append(f"[AUTH] Local UI login: {agent_username}")
    if agent_customer_id:
        logs.append(f"[AUTH] Customer scope: {agent_customer_id}")

    if mode == "mcp_gateway":
        rpc_payload, status, gateway_logs = mcp_gateway_rpc("tools/list")
        tools = normalize_mcp_tools(rpc_payload) if status < 400 else []
        logs.append("[CHECK] Calling MCP Gateway tools/list with YAML credentials only")
        logs.append("[AUTH] Consumer/supervisor/admin headers are not forwarded to MCP Gateway")
        logs.extend(gateway_logs)
        connected = status < 400
        if connected:
            logs.append(f"[SUCCESS] MCP Gateway returned {len(tools)} gateway action items")
        else:
            logs.append(f"[ERROR] MCP Gateway rejected tools/list with HTTP {status}")

        return jsonify(
            {
                "connected": connected,
                "route_mode": mode,
                "route_label": route_label,
                "backend_url": base_url,
                "backend_host": backend_host,
                "mcp_gateway": {
                    "configured": True,
                    "connected": connected,
                    "reachable": status != 502,
                    "url": MCP_GATEWAY_URL,
                    "host": backend_host,
                    "status_code": status,
                    "headers_configured": any(
                        "Credential headers configured: none" not in log for log in gateway_logs
                    ),
                    "logs": gateway_logs,
                    "error": rpc_payload.get("error") if isinstance(rpc_payload, dict) else None,
                },
                "health": None,
                "tool_count": len(tools),
                "role": agent_role,
                "customer_id": agent_customer_id,
                "logs": logs,
                "error": None if connected else rpc_payload.get("error", "MCP Gateway rejected request"),
            }
        ), 200 if connected else status

    try:
        active_headers = {"Accept": "application/json"}
        gateway = None
        ssl_context = None

        logs.append("[CHECK] Calling selected route /health endpoint...")
        health_request = Request(f"{base_url}/health", headers=active_headers)
        with urlopen(health_request, timeout=10, context=ssl_context) as health_response:
            health = json.loads(health_response.read().decode("utf-8"))
            logs.append(f"[SUCCESS] Selected route health check returned HTTP {health_response.status}")

        logs.append("[CHECK] Calling selected route /api/agent/tools endpoint...")
        active_headers.update(
            {
                "X-Policy-Agent-Role": agent_role,
                "X-Policy-Agent-Username": agent_username or "",
                "X-Policy-Agent-Customer-Id": agent_customer_id or "",
            }
        )
        tools_request = Request(
            f"{base_url}/api/agent/tools",
            headers=active_headers,
        )
        with urlopen(tools_request, timeout=10, context=ssl_context) as tools_response:
            tools = json.loads(tools_response.read().decode("utf-8"))
            logs.append(
                f"[SUCCESS] Selected route MCP tool API returned {len(tools)} actions for {agent_role}"
            )

        if gateway:
            logs.extend(gateway["logs"])

        logs.append(f"[COMPLETE] Connected through {route_label}")
        return jsonify(
            {
                "connected": True,
                "route_mode": mode,
                "route_label": route_label,
                "backend_url": base_url,
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
                "route_mode": mode,
                "route_label": route_label,
                "backend_url": base_url,
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
                "route_mode": mode,
                "route_label": route_label,
                "backend_url": base_url,
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
