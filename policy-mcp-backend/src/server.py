"""
Main MCP Server implementation for insurance policy management
"""

import json
import sys
from typing import Any

import mcp.server.stdio
from mcp.server import Server
from mcp.types import Tool, TextContent

from store import PolicyStore
from types_import import CreatePolicyInput, SubmitClaimInput

# Initialize the data store
store = PolicyStore()

# Define available tools
TOOLS: list[Tool] = [
    Tool(
        name="create_policy",
        description="Create a new insurance policy for a customer",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer ID"},
                "policy_type": {
                    "type": "string",
                    "enum": ["auto", "home", "health", "life"],
                    "description": "Type of insurance policy",
                },
                "start_date": {"type": "string", "description": "Policy start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "Policy end date (YYYY-MM-DD)"},
                "premium": {"type": "number", "description": "Annual premium amount"},
                "deductible": {"type": "number", "description": "Deductible amount"},
                "policy_limit": {"type": "number", "description": "Maximum coverage limit"},
                "coverage_options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of coverage option IDs",
                },
            },
            "required": [
                "customer_id",
                "policy_type",
                "start_date",
                "end_date",
                "premium",
                "deductible",
                "policy_limit",
                "coverage_options",
            ],
        },
    ),
    Tool(
        name="get_policy",
        description="Retrieve details for a specific insurance policy",
        inputSchema={
            "type": "object",
            "properties": {"policy_id": {"type": "string", "description": "Policy ID"}},
            "required": ["policy_id"],
        },
    ),
    Tool(
        name="list_policies",
        description="List insurance policies, optionally filtered by customer",
        inputSchema={
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Optional customer ID to filter by",
                }
            },
        },
    ),
    Tool(
        name="get_coverage_options",
        description="Get available coverage options for a policy type",
        inputSchema={
            "type": "object",
            "properties": {
                "policy_type": {"type": "string", "description": "Optional policy type filter"}
            },
        },
    ),
    Tool(
        name="submit_claim",
        description="Submit a claim for an insurance policy",
        inputSchema={
            "type": "object",
            "properties": {
                "policy_id": {"type": "string", "description": "Policy ID"},
                "claim_type": {"type": "string", "description": "Type of claim"},
                "amount": {"type": "number", "description": "Claim amount"},
                "description": {"type": "string", "description": "Claim description"},
            },
            "required": ["policy_id", "claim_type", "amount", "description"],
        },
    ),
    Tool(
        name="list_claims",
        description="List claims, optionally filtered by policy",
        inputSchema={
            "type": "object",
            "properties": {
                "policy_id": {"type": "string", "description": "Optional policy ID to filter by"}
            },
        },
    ),
]


def process_tool_call(tool_name: str, tool_input: dict[str, Any]) -> TextContent:
    """Process a tool call and return the result"""
    try:
        if tool_name == "create_policy":
            input_data = CreatePolicyInput(
                customer_id=tool_input["customer_id"],
                policy_type=tool_input["policy_type"],
                start_date=tool_input["start_date"],
                end_date=tool_input["end_date"],
                premium=tool_input["premium"],
                deductible=tool_input["deductible"],
                policy_limit=tool_input["policy_limit"],
                coverage_options=tool_input["coverage_options"],
            )
            policy = store.create_policy(input_data)
            return TextContent(
                type="text",
                text=json.dumps(policy.__dict__, indent=2),
            )

        elif tool_name == "get_policy":
            policy_id = tool_input["policy_id"]
            policy = store.get_policy(policy_id)
            if not policy:
                return TextContent(
                    type="text",
                    text=f"Policy {policy_id} not found",
                )
            return TextContent(
                type="text",
                text=json.dumps(policy.__dict__, indent=2),
            )

        elif tool_name == "list_policies":
            customer_id = tool_input.get("customer_id")
            policies = store.list_policies(customer_id)
            return TextContent(
                type="text",
                text=json.dumps([p.__dict__ for p in policies], indent=2),
            )

        elif tool_name == "get_coverage_options":
            policy_type = tool_input.get("policy_type")
            options = store.list_coverage_options(policy_type)
            return TextContent(
                type="text",
                text=json.dumps([o.__dict__ for o in options], indent=2),
            )

        elif tool_name == "submit_claim":
            input_data = SubmitClaimInput(
                policy_id=tool_input["policy_id"],
                claim_type=tool_input["claim_type"],
                amount=tool_input["amount"],
                description=tool_input["description"],
            )
            claim = store.submit_claim(input_data)
            return TextContent(
                type="text",
                text=json.dumps(claim.__dict__, indent=2),
            )

        elif tool_name == "list_claims":
            policy_id = tool_input.get("policy_id")
            claims = store.list_claims(policy_id)
            return TextContent(
                type="text",
                text=json.dumps([c.__dict__ for c in claims], indent=2),
            )

        else:
            return TextContent(
                type="text",
                text=f"Unknown tool: {tool_name}",
            )

    except Exception as e:
        return TextContent(
            type="text",
            text=f"Error: {str(e)}",
        )


async def main() -> None:
    """Start the MCP server"""
    from mcp.types import ListToolsRequest, CallToolRequest

    server = Server(name="insurance-policy-mcp-server")

    # Handle tools/list requests
    async def handle_list_tools_request(params: dict[str, Any] | None) -> dict[str, list[Tool]]:
        return {"tools": TOOLS}

    # Handle tools/call requests
    async def handle_call_tool_request(params: dict[str, Any]) -> dict[str, list[TextContent]]:
        tool_name = params.get("name", "")
        tool_input = params.get("arguments", {})
        result = process_tool_call(tool_name, tool_input)
        return {"content": [result]}

    # Register request handlers
    server.add_request_handler("tools/list", dict, handle_list_tools_request)  # type: ignore
    server.add_request_handler("tools/call", dict, handle_call_tool_request)  # type: ignore

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, initialization_options=None)


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
