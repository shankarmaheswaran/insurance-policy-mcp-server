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

## Policy Agent Roles

The backend enforces role-based access for `/api/agent/tools` and `/api/agent/execute` using headers from the laptop Policy Agent UI:

- `X-Policy-Agent-Username`: selected demo login account
- `X-Policy-Agent-Role`: `consumer`, `supervisor`, or `admin`
- `X-Policy-Agent-Customer-Id`: customer scope used by consumer access

Protected agent endpoints require both `X-Policy-Agent-Username` and `X-Policy-Agent-Role`. Requests without a selected login return `401`.

Role access:

- `consumer`: own policy/claim access and claim submission for owned policies.
- `supervisor`: review access across customers and claim submission.
- `admin`: full access, including policy creation.

Seed data includes 10 fictional policy holder profiles with fake phone, address, SSN, passport, income, and family member values. Demo login accounts include 10 consumers, 3 supervisors, and 1 admin. The SSN/passport values are intentionally fake demo identifiers.

## Run MCP stdio Server

```bash
python3 -m src.server
```

Use this command when an MCP client connects to the EC2 instance over SSH or another process manager. The browser-based Policy Agent uses the Flask HTTP API.
