"""Accounting agent: cash, invoices, margins, POs, and human-approved payments.

The MCP `pay` tool is wrapped so every call pauses for a human. Cash only goes out in
this project; no tool ever adds money to an account.
"""

from pydantic_ai import Agent, DeferredToolRequests, DeferredToolResults, ToolApproved, ToolDenied

from .config import get_model, get_shop_mcp, load_prompt, shop_tools
from .models import AccountingReport, PaymentPreview, ShopDeps

ACCOUNTING_TOOLS = {
    "get_cash_position",
    "list_invoices",
    "check_margin",
    "preview_payment",
    "pay",
    "prepare_purchase_order",
    "get_outgoing_payment_tickets",
    "get_incoming_payment_tickets",
}

accounting_agent = Agent(
    get_model(),
    name="accounting",
    deps_type=ShopDeps,
    output_type=[AccountingReport, DeferredToolRequests],
    instructions=load_prompt("accounting"),
    toolsets=[shop_tools(ACCOUNTING_TOOLS, needs_approval={"pay"})],
)


async def resolve_payment_approvals(requests: DeferredToolRequests, deps: ShopDeps) -> DeferredToolResults:
    """For each `pay` the agent asked for: pin a request on the board, ask the human, record the answer."""
    mcp = get_shop_mcp()
    results = DeferredToolResults()
    for call in requests.approvals:
        args = call.args_as_dict()
        request = await mcp.direct_call_tool(
            "request_payment_approval",
            {
                "ticket_id": deps.current_ticket_id,
                "kind": args.get("kind"),
                "ref_id": args.get("ref_id"),
                "account": args.get("account", "checking"),
            },
        )
        request_id = request["payment_request_id"]
        preview = PaymentPreview(**request["preview"], ticket_id=deps.current_ticket_id)
        audit_base = dict(agent="accounting", ticket_id=deps.current_ticket_id, tool_call_id=call.tool_call_id,
                          requested_args=args, payment_request_id=request_id, preview=preview)

        if request["already_requested"] and request["status"] != "awaiting_human_approval":
            deps.audit.append("payment_duplicate_blocked", status=request["status"], **audit_base)
            results.approvals[call.tool_call_id] = ToolDenied(
                f"This payment was already requested as board item #{request_id} (status: {request['status']}). "
                "Do not request it again; report that it is waiting on a human."
            )
            continue

        if request["refused_reason"]:
            deps.audit.append("payment_refused_before_approval", reason=request["refused_reason"], **audit_base)
            results.approvals[call.tool_call_id] = ToolDenied(
                f"Payment refused before approval (board item #{request_id}): {request['refused_reason']}"
            )
            continue

        decision = deps.approver(preview)
        await mcp.direct_call_tool(
            "set_payment_request_status",
            {"payment_request_id": request_id, "approved": decision.approved,
             "approver": decision.approver, "note": decision.note},
        )
        deps.audit.append("payment_approval", decision=decision, **audit_base)
        if decision.approved:
            # The human's name and request id are filled in here, never by the model.
            results.approvals[call.tool_call_id] = ToolApproved(override_args={
                **args,
                "ticket_id": deps.current_ticket_id,
                "approved_by": decision.approver,
                "payment_request_id": request_id,
            })
        else:
            outcome = "denied this payment" if decision.approver else "has not approved this payment yet; it is pending"
            results.approvals[call.tool_call_id] = ToolDenied(
                f"A human {outcome} (board item #{request_id}). No money moved. {decision.note}".strip()
            )
    return results
