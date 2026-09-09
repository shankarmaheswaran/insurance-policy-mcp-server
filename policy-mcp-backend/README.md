# Policy MCP Backend

This folder is the backend to deploy on an AWS EC2 Linux instance. It owns the policy data store, REST API, Policy Agent action execution API, and the MCP stdio server source.

## Run on EC2

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git
python3 -m venv .venv
source .venv/bin/activate
pip install -e "[dev]"
HOST=0.0.0.0 PORT=5000 FLASK_DEBUG=0 python3 app.py
```

Open inbound TCP `5000` in the EC2 security group from your laptop IP only.

## Validate

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/api/policies
python3 -m pytest tests/ -q
```

## MCP Server Header Login for MCP Gateway

OAuth metadata has been removed from this demo backend. The MCP server now uses simple header-based login before exposing `/api/*` and `/insurance-mcp/mcp`.

MCP server URL for Prisma AI Gateway Streamable HTTP:

```text
http://35.165.75.205:5000/insurance-mcp/mcp
```

Required MCP server login headers:

```text
X-MCP-Server-Username: <configured username>
X-MCP-Server-Password: <configured password>
```

Configure the expected header credentials on EC2 with environment variables:

```bash
MCP_SERVER_USERNAME=<username> \
MCP_SERVER_PASSWORD=<password> \
HOST=0.0.0.0 PORT=5000 FLASK_DEBUG=0 python app.py
```

Validate login:

```bash
curl -X POST http://35.165.75.205:5000/mcp-login \
	-H 'X-MCP-Server-Username: <username>' \
	-H 'X-MCP-Server-Password: <password>'
```

Then test Streamable HTTP tool discovery:

```bash
curl http://35.165.75.205:5000/insurance-mcp/mcp \
	-H 'X-MCP-Server-Username: <username>' \
	-H 'X-MCP-Server-Password: <password>'
```

For MCP Gateway mode, the Policy Agent first connects to Prisma AI Gateway with the YAML credentials, then sends the MCP server header login through the gateway before enabling consumer/supervisor/admin login.

## Policy Agent Roles

The backend enforces role-based access for `/api/agent/tools` and `/api/agent/execute` using headers from the laptop Policy Agent UI:

- `X-Policy-Agent-Username`: selected demo login account
- `X-Policy-Agent-Role`: `consumer`, `supervisor`, or `admin`
- `X-Policy-Agent-Customer-Id`: customer scope used by consumer access

Protected agent endpoints require both `X-Policy-Agent-Username` and `X-Policy-Agent-Role`. Requests without a selected login return `401`.

Role access:

- `consumer`: read-only access to own policy holder profile, policies, claims, and coverage options.
- `supervisor`: review access across customers, plus policy creation for consumers, allowed policy edits, renewal, policy status changes, and claim submission. No delete capability is exposed.
- `admin`: full non-delete demo access, including policy maintenance and login inventory.

Seed data includes 10 fictional policy holder profiles with fake phone, address, SSN, passport, income, and family member values. Every seeded customer has at least one policy, and customers can have more than one policy. Demo login accounts include 10 consumers, 3 supervisors, and 1 admin. The SSN/passport values are intentionally fake demo identifiers.

## Run MCP stdio Server

```bash
python3 -m src.server
```

Use this command when an MCP client connects to the EC2 instance over SSH or another process manager. The browser-based Policy Agent uses the Flask HTTP API.
