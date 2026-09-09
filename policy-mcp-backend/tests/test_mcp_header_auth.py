"""
Tests for header-based MCP server login and Streamable HTTP access.
"""

from app import app

MCP_HEADERS = {
    "X-MCP-Server-Username": "mcp-server-demo",
    "X-MCP-Server-Password": "change-me",
}


def test_mcp_login_requires_valid_headers() -> None:
    """MCP login rejects missing headers."""
    client = app.test_client()

    response = client.post("/mcp-login")
    data = response.get_json()

    assert response.status_code == 401
    assert data["authenticated"] is False


def test_mcp_login_accepts_valid_headers() -> None:
    """MCP login accepts configured normal headers."""
    client = app.test_client()

    response = client.post("/mcp-login", headers=MCP_HEADERS)
    data = response.get_json()

    assert response.status_code == 200
    assert data["authenticated"] is True
    assert data["auth_type"] == "headers"


def test_api_requires_mcp_server_login_headers() -> None:
    """Protected API routes require MCP server login headers before role login."""
    client = app.test_client()

    response = client.get("/api/agent/logins")

    assert response.status_code == 401
    assert response.get_json()["error"] == "MCP server header login required"


def test_http_mcp_endpoint_requires_mcp_server_login_headers() -> None:
    """Streamable HTTP MCP endpoint rejects missing MCP server headers."""
    client = app.test_client()

    response = client.get("/insurance-mcp/mcp")

    assert response.status_code == 401
    assert response.get_json()["error"] == "MCP server header login required"


def test_http_mcp_endpoint_metadata() -> None:
    """Streamable HTTP MCP endpoint is reachable after header login."""
    client = app.test_client()

    response = client.get("/insurance-mcp/mcp", headers=MCP_HEADERS)
    data = response.get_json()

    assert response.status_code == 200
    assert data["service"] == "insurance-policy-mcp-server"
    assert data["protocol"] == "mcp-streamable-http"
    assert response.headers["MCP-Protocol-Version"]
    assert response.headers["Mcp-Session-Id"]
    assert "tools/list" in data["methods"]


def test_http_mcp_endpoint_sse_get() -> None:
    """Streamable HTTP MCP endpoint supports SSE-style GET after header login."""
    client = app.test_client()
    headers = {**MCP_HEADERS, "Accept": "text/event-stream"}

    response = client.get("/insurance-mcp/mcp", headers=headers)

    assert response.status_code == 200
    assert response.content_type.startswith("text/event-stream")
    assert b"event: endpoint" in response.data


def test_http_mcp_endpoint_tools_list() -> None:
    """Streamable HTTP MCP endpoint supports tools/list JSON-RPC after header login."""
    client = app.test_client()

    response = client.post(
        "/insurance-mcp/mcp",
        headers=MCP_HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["jsonrpc"] == "2.0"
    assert response.headers["MCP-Protocol-Version"]
    assert response.headers["Mcp-Session-Id"]
    assert data["result"]["tools"]
    assert data["result"]["tools"][0]["inputSchema"]["type"] == "object"


def test_http_mcp_endpoint_initialize() -> None:
    """Streamable HTTP MCP endpoint supports initialize JSON-RPC after header login."""
    client = app.test_client()

    response = client.post(
        "/insurance-mcp/mcp",
        headers=MCP_HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["result"]["capabilities"]["tools"] == {}
    assert data["result"]["serverInfo"]["name"] == "insurance-policy-mcp-server"
