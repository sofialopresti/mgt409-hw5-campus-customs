"""Full run: reset the database through MCP, then have the Boss work every open ticket.

    .venv/bin/python -m backend.run

Payments stop and ask the person at the terminal. If nobody is at the terminal, every payment
is left on the board as pending human approval. Every step is appended to output/audit_trail.json.
The desk API (backend/main.py) uses run_ticket() to work one ticket at a time.
"""

import asyncio
import sys
import time

from pydantic_ai import UsageLimits

from .audit import AuditTrail, live_tool_calls
from .boss import BOSS_TOOLS, boss_agent
from .config import MODEL_NAME, get_shop_mcp
from .models import ApprovalDecision, PaymentPreview, ShopDeps, TicketDecision

TICKET_REQUEST_LIMIT = 60


def terminal_approver(preview: PaymentPreview) -> ApprovalDecision:
    """Ask the human at the keyboard to approve or deny one payment."""
    if not sys.stdin.isatty():
        return ApprovalDecision(approved=False, note="No human at the terminal; left pending on the board.")
    print("\n  ┌─ PAYMENT NEEDS YOUR APPROVAL " + "─" * 30)
    print(f"  │ Ticket {preview.ticket_id}: pay ${preview.amount:,.2f} to {preview.payee}")
    print(f"  │ {preview.description}")
    print(f"  │ {preview.account}: ${preview.cash_before:,.2f} → ${preview.cash_after:,.2f}")
    print("  └" + "─" * 59)
    if input("  Approve this payment? [y/N] ").strip().lower() not in {"y", "yes"}:
        return ApprovalDecision(approved=False, approver="human", note="Denied at the terminal.")
    name = input("  Your name (saved as payments.approved_by): ").strip() or "human"
    return ApprovalDecision(approved=True, approver=name)


async def run_ticket(ticket_id: int, deps: ShopDeps) -> TicketDecision | None:
    """Have the Boss work one ticket and save its final call. Returns None if the run failed."""
    mcp, audit = get_shop_mcp(), deps.audit
    deps.current_ticket_id = ticket_id
    task = f"Handle ticket {ticket_id}. Today is {deps.shop_date}."
    started = time.monotonic()
    audit.append("agent_started", agent="boss", ticket_id=ticket_id, task=task)
    try:
        result = await boss_agent.run(
            task,
            deps=deps,
            usage_limits=UsageLimits(request_limit=TICKET_REQUEST_LIMIT),
            event_stream_handler=live_tool_calls(audit, "boss", ticket_id),
        )
    except Exception as exc:  # the ticket stays as it was; the error is audited
        print(f"  Ticket {ticket_id} failed: {type(exc).__name__}: {exc}\n")
        audit.append("agent_error", agent="boss", ticket_id=ticket_id, task=task, error=f"{type(exc).__name__}: {exc}")
        return None
    decision = result.output
    decision.ticket_id = ticket_id
    audit.agent_loop("boss", ticket_id, task, result, started, tools_available=sorted(BOSS_TOOLS))
    board_item = await mcp.direct_call_tool("record_ticket_decision", {
        "ticket_id": ticket_id,
        "status": decision.status,
        "final_call": decision.final_call,
        "human_follow_ups": decision.human_follow_ups,
        "agents_consulted": decision.agents_consulted,
    })
    audit.append("ticket_decision", agent="boss", ticket_id=ticket_id, decision=decision,
                 board_item_id=board_item["id"])
    print(f"  BOSS FINAL CALL [{decision.status}]: {decision.final_call}\n")
    return decision


async def run_all() -> None:
    mcp = get_shop_mcp()
    audit = AuditTrail()
    async with mcp:
        start = await mcp.direct_call_tool("start_full_run", {})
        today, ticket_ids = start["date_today"], start["open_ticket_ids"]
        audit.append("run_started", model=MODEL_NAME, shop_date=today, open_ticket_ids=ticket_ids,
                     database_reset=True, interactive_approver=sys.stdin.isatty())
        print(f"Database reset to original values. Shop date (desk.date_today): {today}. Model: {MODEL_NAME}")
        print(f"Open tickets: {ticket_ids}\n")

        deps = ShopDeps(approver=terminal_approver, audit=audit, shop_date=today)
        outcomes = {}
        for ticket_id in ticket_ids:
            print(f"── Ticket {ticket_id} " + "─" * 50)
            decision = await run_ticket(ticket_id, deps)
            outcomes[ticket_id] = decision.status if decision else "error (unchanged)"

        audit.append("run_finished", ticket_outcomes=outcomes)
    print(f"Board: output/board.md\nAudit trail: output/audit_trail.json (run_id {audit.run_id})")


def main() -> None:
    asyncio.run(run_all())


if __name__ == "__main__":
    main()
