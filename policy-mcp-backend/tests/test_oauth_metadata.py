"""
Tests for OAuth 2.1 metadata endpoints exposed by the backend.
"""

from app import app


def test_oauth_protected_resource_metadata() -> None:
    """Protected resource metadata advertises the MCP resource and auth server."""
    client = app.test_client()

    response = client.get("/.well-known/oauth-protected-resource")
    data = response.get_json()

    assert response.status_code == 200
    assert data["resource"].endswith("/insurance-mcp/mcp")
    assert data["authorization_servers"]
    assert "Bearer" in data["bearer_methods_supported"]
    assert "mcp:tools" in data["scopes_supported"]


def test_oauth_authorization_server_metadata() -> None:
    """Authorization server metadata contains OAuth 2.1 discovery fields."""
    client = app.test_client()

    response = client.get("/.well-known/oauth-authorization-server")
    data = response.get_json()

    assert response.status_code == 200
    assert data["issuer"]
    assert data["authorization_endpoint"].endswith("/oauth/authorize")
    assert data["token_endpoint"].endswith("/oauth/token")
    assert data["jwks_uri"].endswith("/oauth/jwks")
    assert "authorization_code" in data["grant_types_supported"]
    assert "S256" in data["code_challenge_methods_supported"]


def test_oauth_jwks_metadata() -> None:
    """JWKS endpoint is available for gateway discovery."""
    client = app.test_client()

    response = client.get("/oauth/jwks")
    data = response.get_json()

    assert response.status_code == 200
    assert "keys" in data


def test_oauth_introspection_demo_token() -> None:
    """Demo introspection endpoint can validate the configured bearer token."""
    client = app.test_client()

    response = client.post("/oauth/introspect", data={"token": ""})
    data = response.get_json()

    assert response.status_code == 200
    assert data["active"] is False


def test_http_mcp_endpoint_metadata() -> None:
    """Advertised MCP resource endpoint is reachable over HTTP."""
    client = app.test_client()

    response = client.get("/insurance-mcp/mcp")
    data = response.get_json()

    assert response.status_code == 200
    assert data["service"] == "insurance-policy-mcp-server"
    assert "tools/list" in data["methods"]


def test_http_mcp_endpoint_tools_list() -> None:
    """Advertised MCP resource supports tools/list JSON-RPC discovery."""
    client = app.test_client()

    response = client.post(
        "/insurance-mcp/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["jsonrpc"] == "2.0"
    assert data["result"]["tools"]
    assert data["result"]["tools"][0]["inputSchema"]["type"] == "object"
