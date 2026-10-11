"""Append-only audit trail: output/audit_trail.json.

Every agent start, tool call, finished agent loop, payment approval, ticket decision, and error is
appended as it happens.
Entries from earlier runs are never removed; each run has its own run_id.
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import AgentRunResult, FunctionToolCallEvent
from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart
from pydantic_core import to_jsonable_python

from .config import MODEL_NAME, OUTPUT_DIR

AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"


def _jsonable(value: Any) -> Any:
    return to_jsonable_python(value, fallback=str)


def live_tool_calls(audit: "AuditTrail", agent: str, ticket_id: int | None):
    """PydanticAI event handler: append a tool_call entry the moment an agent calls a tool."""

    async def handler(ctx, events):
        async for event in events:
            if isinstance(event, FunctionToolCallEvent):
                audit.append("tool_call", agent=agent, ticket_id=ticket_id,
                             tool_calls=[{"tool": event.part.tool_name, "args": event.part.args_as_dict()}])

    return handler


class AuditTrail:
    def __init__(self, path=AUDIT_PATH):
        self.path = path
        self.run_id = f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"

    def append(self, event: str, **fields: Any) -> dict:
        entries = json.loads(self.path.read_text()) if self.path.exists() else []
        entry = {
            "seq": len(entries) + 1,
            "run_id": self.run_id,
            "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "event": event,
            **_jsonable(fields),
        }
        entries.append(entry)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, indent=2))
        os.replace(tmp, self.path)  # never leave a half-written file
        return entry

    def agent_loop(
        self, agent: str, ticket_id: int | None, task: str, result: AgentRunResult, started: float, **extra: Any
    ) -> dict:
        """One finished agent loop: the task, every tool call with args and result, the output, and usage."""
        calls: dict[str, dict] = {}
        model_turns = 0
        for message in result.all_messages():
            if isinstance(message, ModelResponse):
                model_turns += 1
                for part in message.parts:
                    if isinstance(part, ToolCallPart):
                        calls[part.tool_call_id] = {"tool": part.tool_name, "args": part.args_as_dict()}
            elif isinstance(message, ModelRequest):
                for part in message.parts:
                    if isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                        calls[part.tool_call_id].update(outcome="returned", result=part.content)
                    elif isinstance(part, RetryPromptPart) and part.tool_call_id in calls:
                        calls[part.tool_call_id].update(outcome="error_retried", result=part.content)
        usage = result.usage
        return self.append(
            "agent_loop",
            agent=agent,
            ticket_id=ticket_id,
            model=MODEL_NAME,
            task=task,
            tool_calls=[{"tool_call_id": k, **v} for k, v in calls.items()],
            output=result.output,
            model_turns=model_turns,
            usage={
                "requests": usage.requests,
                "tool_calls": usage.tool_calls,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            },
            duration_seconds=round(time.monotonic() - started, 2),
            **extra,
        )
