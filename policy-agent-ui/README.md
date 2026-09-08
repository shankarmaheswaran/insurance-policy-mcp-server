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

## Validate

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/api/agent/tools
```

If `POLICY_BACKEND_URL` is missing or EC2 is unreachable, the UI still loads, but API calls return an error explaining the backend connection problem.
