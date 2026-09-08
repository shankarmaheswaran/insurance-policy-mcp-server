# Policy Agent UI

This folder runs on your laptop. It renders the dashboard and Policy Agent pages locally, then forwards all policy, claim, stats, and agent API calls to the backend hosted on AWS EC2.

## Run on Your Laptop

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
POLICY_BACKEND_URL=http://<ec2-public-ip-or-dns>:5000 python3 app.py
```

Open:

- Dashboard: `http://127.0.0.1:5000/`
- Policy Agent: `http://127.0.0.1:5000/agent`

## Agent Roles

The Policy Agent login supports three demo roles:

- `consumer`: can view policies and claims for the selected customer scope, view coverage options, and submit claims for owned policies.
- `supervisor`: can review policies, claims, and coverage options across customers, and submit claims.
- `admin`: has full access, including creating new policies.

The login picker loads 10 consumer accounts, 3 supervisor accounts, and 1 admin account from the EC2 backend. The selected role and customer scope are sent to the EC2 backend on every Policy Agent request.

The Policy Agent starts signed out on each page load. Remote MCP connection details, action lists, inputs, outputs, and trace logs stay hidden until a demo login is selected and the user clicks `Login to Policy Agent`.

## Validate

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/api/agent/tools
```

If `POLICY_BACKEND_URL` is missing or EC2 is unreachable, the UI still loads, but API calls return an error explaining the backend connection problem.
