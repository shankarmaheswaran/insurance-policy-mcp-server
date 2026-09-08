# Insurance Policy MCP Server

A Model Context Protocol (MCP) server for managing fictional insurance policies. This server provides tools and resources for querying, creating, and managing insurance policies.

## Features

- **Policy Management**: Create, retrieve, and update insurance policies
- **Coverage Tools**: Query available coverage types and policy limits
- **Claims Processing**: Manage claims submissions and tracking
- **Resource Access**: Browse policy database and coverage catalogs

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Installation

```bash
pip install -e .
```

### Development

Install with development dependencies:

```bash
pip install -e ".[dev]"
```

### Running the Server

```bash
python -m src.server
```

Or if installed as a script:

```bash
insurance-mcp-server
```

### Running the Web Dashboard and Policy Agent

Run the Flask web app locally:

```bash
python3 app.py
```

Open:

- Dashboard: `http://127.0.0.1:5000/`
- Policy Agent: `http://127.0.0.1:5000/agent`

### Split Laptop Agent and EC2 Backend Setup

Use this setup when you want the Policy Agent UI on your laptop and the insurance policy backend on an AWS EC2 Linux instance.

On the EC2 instance, install and run the backend so it accepts network traffic:

```bash
sudo dnf update -y
sudo dnf install -y python3 python3-pip git
git clone <your-repo-url>
cd <your-repo-folder>
python3 -m venv .venv
source .venv/bin/activate
pip install -e "[dev]"
HOST=0.0.0.0 PORT=5000 FLASK_DEBUG=0 python3 app.py
```

In the EC2 security group, allow inbound TCP `5000` from your laptop IP only. Avoid opening this demo server to the whole internet.

On your laptop, run the Policy Agent UI and point it at EC2:

```bash
cd <your-local-repo-folder>
python3 -m venv .venv
source .venv/bin/activate
pip install -e "[dev]"
POLICY_BACKEND_URL=http://<ec2-public-ip-or-dns>:5000 python3 app.py
```

Then open `http://127.0.0.1:5000/agent`. The local Policy Agent will forward policy, claim, stats, and agent tool requests to the EC2 backend.

For the MCP stdio server itself, run this on EC2 when connecting through an MCP client over SSH:

```bash
python3 -m src.server
```

The browser-based Policy Agent uses the Flask HTTP API because standard MCP stdio is not directly callable from a browser.

### Testing

Run the test suite:

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=src
```

### Linting and Formatting

Format code:

```bash
black .
isort .
```

Run linter:

```bash
pylint src/
```

Run type checker:

```bash
mypy src/
```

## Architecture

The server implements the Model Context Protocol (MCP) specification and provides:

- **Tools**: Functions that can be called by LLM clients
  - `create_policy`: Create a new insurance policy
  - `get_policy`: Retrieve policy details
  - `list_policies`: List available policies
  - `get_coverage_options`: Query available coverage types
  - `submit_claim`: Submit an insurance claim
  - `list_claims`: List insurance claims

- **Resources**: Data resources that clients can access
  - `insurance://policies` - Policy database entries
  - `insurance://coverage-options` - Coverage catalogs

- **Prompts**: Pre-built prompt templates for common operations
  - `policy_summary`: Generate a summary of a policy
  - `claim_guidance`: Provide claim submission guidance

## Project Structure

```
policy-agent-ui/
  ├── app.py          # Laptop-only dashboard and Policy Agent proxy UI
  ├── templates/      # Local UI templates
  └── static/         # Local UI JavaScript and CSS
policy-mcp-backend/
  ├── app.py          # EC2 backend HTTP API
  ├── src/            # MCP server and policy business logic
  └── tests/          # Backend unit tests
src/
  ├── server.py       # Main MCP server implementation
  ├── store.py        # In-memory data store
  ├── types_import.py # Type definitions and dataclasses
tests/
  └── test_store.py   # Unit tests
.vscode/
  └── launch.json     # VS Code debugger configuration
pyproject.toml        # Project configuration
requirements.txt      # Dependency list
```

Use `policy-agent-ui/` on your laptop and `policy-mcp-backend/` on EC2 for a clean split deployment. The root-level files remain available for local combined development.

## Environment Variables

- `HOST`: Flask bind host. Use `0.0.0.0` on EC2. Defaults to `127.0.0.1`.
- `PORT`: Flask port. Defaults to `5000`.
- `FLASK_DEBUG`: Set `0` on EC2 and `1` during local development. Defaults to `1`.
- `POLICY_BACKEND_URL`: Optional remote backend base URL. When set on your laptop, the dashboard and Policy Agent forward API calls to the EC2 backend.

## Configuration Files

- **pyproject.toml**: Project metadata, dependencies, and tool configuration
- **.pylintrc**: Linting rules
- **.flake8**: Code style checking
- **pyproject.toml**: Black and isort formatting rules

## Debugging with VS Code

This project includes a VS Code MCP launch configuration. To debug:

1. Press `Ctrl+Shift+D` (or `Cmd+Shift+D` on macOS)
2. Select "Python: Insurance Policy Server" from the debug dropdown
3. Press F5 to start debugging

## MCP Documentation

For more information about the Model Context Protocol:
- [MCP Specification](https://modelcontextprotocol.io)
- [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Quick Start Guide](https://modelcontextprotocol.io/quickstart)

## Sample Data

The store initializes with:
- **Policies**: POL-1000 (auto, CUST-001), POL-1001 (home, CUST-002)
- **Coverage Options**: Comprehensive, Collision, Homeowners Liability, Medical Coverage
- **Claims**: CLM-5000 (approved collision claim on POL-1000)

## License

MIT
