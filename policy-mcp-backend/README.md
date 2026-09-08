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

## Run MCP stdio Server

```bash
python3 -m src.server
```

Use this command when an MCP client connects to the EC2 instance over SSH or another process manager. The browser-based Policy Agent uses the Flask HTTP API.
