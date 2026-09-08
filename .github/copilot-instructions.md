---
applyTo: "**"
---

# Insurance Policy MCP Server - Copilot Instructions

## Overview

This is a Model Context Protocol (MCP) server for managing fictional insurance policies. It provides tools and resources for policy management, coverage options, and claims processing. Built with Python 3.10+.

## Project Structure

- `src/` - Python source files
  - `server.py` - Main MCP server implementation
  - `store.py` - In-memory data store for policies and claims
  - `types_import.py` - Dataclass definitions and types
- `tests/` - Test files
  - `test_store.py` - Unit tests using pytest
- `.vscode/` - VS Code configuration
  - `launch.json` - Python debugger configuration
- `.github/` - GitHub configuration
  - `copilot-instructions.md` - This file

## Available Tools

The server exposes the following MCP tools:

1. **create_policy** - Create a new insurance policy
2. **get_policy** - Retrieve policy details
3. **list_policies** - List policies (with optional customer filter)
4. **get_coverage_options** - Query available coverage types
5. **submit_claim** - Submit an insurance claim
6. **list_claims** - List claims (with optional policy filter)

## Available Resources

- `insurance://policies` - Policies database
- `insurance://coverage-options` - Coverage catalog

## Available Prompts

- `policy_summary` - Generate a policy summary
- `claim_guidance` - Provide claim submission guidance

## Development

### Install dependencies
```bash
pip install -e ".[dev]"
```

### Run the server
```bash
python -m src.server
```

### Run tests
```bash
pytest
```

### Lint and format code
```bash
black .        # Format code
isort .        # Sort imports
pylint src/    # Run linter
mypy src/      # Type checking
```

## Debugging with VS Code

1. Press `Ctrl+Shift+D` (or `Cmd+Shift+D` on macOS)
2. Select "Python: Insurance Policy Server" from the dropdown
3. Press F5 to start debugging

## Key Features

- Type-safe implementation using Python dataclasses
- In-memory data store with sample data
- Comprehensive tool definitions with JSON schema validation
- Resource access for policy and coverage data
- Prompt templates for common operations
- Unit tests with pytest and 80%+ coverage target
- Full type hints with mypy strict mode

## MCP SDK Reference

This project uses the official Python SDK:
- [Python SDK Repository](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://modelcontextprotocol.io)
- [Quick Start Guide](https://modelcontextprotocol.io/quickstart)

## Sample Data

### Pre-loaded Policies
- POL-1000: Auto insurance for CUST-001
- POL-1001: Home insurance for CUST-002

### Coverage Options
- cov-001: Comprehensive Coverage (Auto)
- cov-002: Collision Coverage (Auto)
- cov-003: Homeowners Liability (Home)
- cov-004: Medical Coverage (Health)

### Sample Claims
- CLM-5000: Approved collision claim on POL-1000 for $5,000

## Best Practices

1. Follow the organization's engineering principles (DRY, TDD, coverage >80%)
2. Update tests when adding new tools or resources
3. Keep the data store in sync with realistic insurance scenarios
4. Document new tools and prompts in this file
5. Use type hints for all function parameters and return types
6. Maintain test coverage above 80% for new code
