"""Shared settings: paths, the Portkey-backed model, the MCP connection, and prompt loading.

Agents get shop data ONLY through the Campus Customs MCP server (mcp_server/server.py).
Each agent sees just the MCP tools for its specialty.
"""

import os
import sys
from functools import cache
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.toolsets import AbstractToolset

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
PROMPTS_DIR = BACKEND_DIR / "prompts"
MCP_SERVER_SCRIPT = PROJECT_DIR / "mcp_server" / "server.py"
VENV_PYTHON = PROJECT_DIR / ".venv" / "bin" / "python"

MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# MCP tools only backend/run.py and backend/main.py may call. They are never given to an agent.
ORCHESTRATOR_ONLY_TOOLS = {
    "list_tickets",
    "approve_purchase_order",
    "start_full_run",
    "request_payment_approval",
    "set_payment_request_status",
    "record_ticket_decision",
}

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")


@cache
def get_model() -> OpenAIResponsesModel:
    """One shared model client for every agent."""
    load_dotenv(find_dotenv())
    portkey_api_key = os.getenv("PORTKEY_API_KEY")
    if not portkey_api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the .env file.")
    # Never serve agents from Portkey's response cache: cached tool calls come back with ids the
    # Responses API rejects, and agents should always see fresh shop data.
    client = AsyncOpenAI(
        base_url=PORTKEY_BASE_URL,
        api_key=portkey_api_key,
        default_headers={"x-portkey-cache-force-refresh": "true"},
    )
    provider = OpenAIProvider(openai_client=client)
    # Responses API: gpt-6-luna doesn't allow tools + reasoning on /chat/completions.
    return OpenAIResponsesModel(MODEL_NAME, provider=provider)


@cache
def get_shop_mcp() -> MCPToolset:
    """One stdio connection to the Campus Customs MCP server, shared by every agent."""
    transport = StdioTransport(
        command=str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)),
        args=[str(MCP_SERVER_SCRIPT)],
        cwd=str(PROJECT_DIR),
        log_file=OUTPUT_DIR / "mcp_server.log",
    )
    return MCPToolset(transport, id="campus-customs")


def shop_tools(names: set[str], needs_approval: set[str] = frozenset()) -> AbstractToolset:
    """The subset of MCP tools one agent may use; tools in needs_approval pause for a human."""
    if names & ORCHESTRATOR_ONLY_TOOLS:
        raise ValueError(f"Agents may not use orchestrator tools: {names & ORCHESTRATOR_ONLY_TOOLS}")
    toolset = get_shop_mcp().filtered(lambda ctx, tool_def: tool_def.name in names)
    if needs_approval:
        toolset = toolset.approval_required(lambda ctx, tool_def, args: tool_def.name in needs_approval)
    return toolset


def load_prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text()
