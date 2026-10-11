"""Campus Customs desk API (FastAPI).

Start it from the backend/ folder:
    uvicorn main:app --reload --port 8000

Shop data comes only from the Campus Customs MCP server. Agents only *prepare* payments; money
moves when a human clicks Approve (POST /approvals/{id}/approve). Interactive docs: /docs.
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:  # lets `uvicorn main:app` run from inside backend/
    sys.path.insert(0, str(PROJECT_DIR))

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from backend.audit import AUDIT_PATH, AuditTrail  # noqa: E402
from backend.config import get_shop_mcp  # noqa: E402
from backend.models import (  # noqa: E402
    AgentEvent,
    ApprovalDecision,
    ApproveRequest,
    PaymentPreview,
    RunStatus,
    ShopDeps,
    TicketView,
)
from backend.run import run_ticket  # noqa: E402

PENDING_PAYMENT = {"awaiting_human_approval", "pending_human_approval"}
PENDING_PO = {"pending_human_check", "blocked_unpaid_invoice"}

runs: dict[str, RunStatus] = {}
tasks: dict[str, asyncio.Task] = {}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def board_approver(preview: PaymentPreview) -> ApprovalDecision:
    """In the API, agents never get a yes: payments wait on the board until a human clicks Approve."""
    return ApprovalDecision(approved=False, note="Waiting for a human to click Approve on the board.")


def active_run() -> RunStatus | None:
    return next((r for r in runs.values() if r.state == "running"), None)


async def mcp_call(tool: str, args: dict | None = None):
    """Call a Campus Customs MCP tool; turn MCP refusals into a 409 the board can show."""
    try:
        return await get_shop_mcp().direct_call_tool(tool, args or {})
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with get_shop_mcp():  # one MCP connection for the life of the server
        yield
    for task in tasks.values():
        task.cancel()


app = FastAPI(title="Campus Customs Desk API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # the Vite board (npm run dev)
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- tickets

@app.get("/tickets", response_model=list[TicketView])
async def list_tickets():
    """All three tickets and whether each is resolved (the agents finished it) or still open.
    `status` keeps the Boss's exact outcome, e.g. waiting_on_human."""
    data = await mcp_call("list_tickets")
    return [
        TicketView(**t, state="open" if t["status"] == "open" else "resolved")
        for t in data["tickets"]
    ]


@app.post("/tickets/{ticket_id}/run", response_model=RunStatus, status_code=202)
async def run_agents_on_ticket(ticket_id: int):
    """Start the agent team on one ticket in the background. Poll /runs/{run_id} or /events."""
    if busy := active_run():
        raise HTTPException(409, f"Agents are already working on ticket {busy.ticket_id} (run {busy.run_id}).")
    data = await mcp_call("list_tickets")
    ticket = next((t for t in data["tickets"] if t["id"] == ticket_id), None)
    if ticket is None:
        raise HTTPException(404, f"No ticket with id {ticket_id}.")
    if ticket["status"] == "resolved":
        raise HTTPException(409, f"Ticket {ticket_id} is already resolved. POST /reset for a fresh run.")

    audit = AuditTrail()
    status = RunStatus(run_id=audit.run_id, ticket_id=ticket_id, state="running", started_at=now())
    runs[audit.run_id] = status
    audit.append("run_started", source="desk_api", shop_date=data["date_today"], ticket_id=ticket_id,
                 database_reset=False, interactive_approver=False)
    deps = ShopDeps(approver=board_approver, audit=audit, shop_date=data["date_today"])

    async def work():
        try:
            decision = await run_ticket(ticket_id, deps)
            status.decision = decision
            status.state = "finished" if decision else "failed"
            status.error = None if decision else "The Boss could not finish; see /events."
        except Exception as exc:
            status.state, status.error = "failed", f"{type(exc).__name__}: {exc}"
        finally:
            status.finished_at = now()
            audit.append("run_finished", source="desk_api", ticket_outcomes={ticket_id: status.state})

    tasks[audit.run_id] = asyncio.create_task(work())
    return status


@app.get("/runs/{run_id}", response_model=RunStatus)
async def get_run(run_id: str):
    """Whether a ticket run is still going, and the Boss's final call once it's done."""
    if run_id not in runs:
        raise HTTPException(404, f"No run {run_id} since the server started.")
    return runs[run_id]


# ---------------------------------------------------------------- events (for the board)

def to_event(entry: dict) -> AgentEvent:
    calls = entry.get("tool_calls") or []
    calls = [c for c in calls if not c.get("tool", "").startswith("final_result")]
    output = entry.get("output") or {}
    decision = entry.get("decision") or {}
    preview = entry.get("preview") or {}
    if entry["event"] == "agent_started":
        summary = entry.get("task")
    elif entry["event"] == "tool_call":
        summary = f"Using {', '.join(c['tool'] for c in calls)}" if calls else None
    elif entry["event"] == "agent_loop":
        summary = output.get("summary") or output.get("final_call")
    elif entry["event"] == "ticket_decision":
        summary = f"[{decision.get('status')}] {decision.get('final_call')}"
    elif preview:
        who = decision.get("approver") or "nobody yet"
        summary = (f"Pay ${preview.get('amount', 0):,.2f} to {preview.get('payee')}: "
                   f"{'approved by ' + who if decision.get('approved') else 'not approved (' + who + ')'}")
    else:
        summary = entry.get("error") or entry.get("reason") or entry.get("message")
    return AgentEvent(
        seq=entry["seq"],
        run_id=entry["run_id"],
        logged_at=entry["logged_at"],
        event=entry["event"],
        agent=entry.get("agent"),
        ticket_id=entry.get("ticket_id"),
        summary=summary,
        tools_used=sorted({c["tool"] for c in calls}),
        tool_calls=[{"tool": c["tool"], "args": c.get("args"), "outcome": c.get("outcome")} for c in calls],
        detail=entry.get("output") or entry.get("decision") or entry.get("result"),
    )


@app.get("/events", response_model=list[AgentEvent])
async def recent_events(
    limit: int = Query(50, ge=1, le=500),
    ticket_id: int | None = None,
    since_seq: int = Query(0, ge=0, description="Only events after this seq (for refreshing the board)."),
):
    """Recent agent events from the audit trail: what each agent did and the tools it used."""
    entries = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
    entries = [e for e in entries if e["seq"] > since_seq and (ticket_id is None or e.get("ticket_id") == ticket_id)]
    return [to_event(e) for e in entries[-limit:]]


# ---------------------------------------------------------------- approvals

@app.get("/approvals")
async def pending_approvals():
    """Payment requests and purchase orders on the board waiting for a human."""
    items = await mcp_call("view_board")
    return [
        i for i in items
        if (i["kind"] == "payment_request" and i["status"] in PENDING_PAYMENT)
        or (i["kind"] == "purchase_order" and i["status"] in PENDING_PO)
    ]


@app.post("/approvals/{item_id}/approve")
async def approve(item_id: int, body: ApproveRequest):
    """A human clicked Approve: pay a payment request, or approve a purchase order."""
    if busy := active_run():
        raise HTTPException(409, f"Wait for the agents to finish ticket {busy.ticket_id} before approving.")
    items = await mcp_call("view_board")
    item = next((i for i in items if i["id"] == item_id), None)
    if item is None:
        raise HTTPException(404, f"No board item #{item_id}.")
    audit = AuditTrail()
    approver = body.approved_by.strip()

    if item["kind"] == "payment_request":
        if item["status"] not in PENDING_PAYMENT:
            raise HTTPException(409, f"Payment request #{item_id} is '{item['status']}', not waiting for approval.")
        d = item["data"]
        await mcp_call("set_payment_request_status",
                       {"payment_request_id": item_id, "approved": True, "approver": approver})
        audit.append("payment_approval", source="desk_api", agent="human", ticket_id=item["ticket_id"],
                     payment_request_id=item_id, preview=d,
                     decision={"approved": True, "approver": approver})
        result = await mcp_call("pay", {
            "kind": d["kind"], "ref_id": d["ref_id"], "ticket_id": item["ticket_id"], "account": d["account"],
            "approved_by": approver, "payment_request_id": item_id,
        })
        audit.append("payment_result", source="desk_api", agent="human", ticket_id=item["ticket_id"],
                     payment_request_id=item_id, result=result, message=result["message"])
        return {"approved": item_id, "kind": "payment", "result": result}

    if item["kind"] == "purchase_order":
        try:
            result = await get_shop_mcp().direct_call_tool(
                "approve_purchase_order", {"purchase_order_id": item_id, "approved_by": approver})
        except Exception as exc:
            audit.append("purchase_order_refused", source="desk_api", agent="human", ticket_id=item["ticket_id"],
                         purchase_order_id=item_id, reason=str(exc))
            raise HTTPException(409, str(exc)) from exc
        audit.append("purchase_order_approval", source="desk_api", agent="human", ticket_id=item["ticket_id"],
                     purchase_order_id=item_id, approved_by=approver, message=f"PO #{item_id} approved")
        return {"approved": item_id, "kind": "purchase_order", "result": result}

    raise HTTPException(400, f"Board item #{item_id} is a {item['kind']}; only payments and POs need approval.")


# ---------------------------------------------------------------- cash & reset

@app.get("/cash")
async def checking_balance():
    """The checking balance from cash_accounts."""
    cash = await mcp_call("get_cash_position", {"account": "checking"})
    return {"account": cash["account"], "balance": cash["balance"], "as_of": cash["as_of"]}


@app.post("/reset")
async def reset_database():
    """Reset the working database to the original values and clear the board, for a fresh run."""
    if busy := active_run():
        raise HTTPException(409, f"Agents are working on ticket {busy.ticket_id}; reset when they finish.")
    result = await mcp_call("start_full_run")
    AuditTrail().append("database_reset", source="desk_api", shop_date=result["date_today"],
                        message="Working database reset to original values; board cleared.")
    return {"reset": True, **result}
