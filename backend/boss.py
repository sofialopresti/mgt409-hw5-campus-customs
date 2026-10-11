"""Boss agent: reads each ticket, delegates to the right specialists, and makes the final call."""

import time

from pydantic_ai import Agent, DeferredToolRequests, RunContext

from .accounting import accounting_agent, resolve_payment_approvals
from .audit import live_tool_calls
from .config import get_model, load_prompt, shop_tools
from .customer_service import customer_service_agent
from .facilities import facilities_agent
from .inventory import inventory_agent
from .models import (
    AccountingReport,
    CustomerServiceReport,
    FacilitiesReport,
    InventoryReport,
    ShopDeps,
    SpecialistReport,
    TicketDecision,
)

BOSS_TOOLS = {
    "get_ticket",
    "view_board",
    "get_outgoing_payment_tickets",
    "get_incoming_payment_tickets",
    "get_inventory_change_tickets",
}

boss_agent = Agent(
    get_model(),
    name="boss",
    deps_type=ShopDeps,
    output_type=TicketDecision,
    instructions=load_prompt("boss"),
    toolsets=[shop_tools(BOSS_TOOLS)],
)


async def delegate(ctx: RunContext[ShopDeps], specialist: Agent, task: str) -> SpecialistReport:
    """Run a specialist's own agent loop on a task, pausing for human approval when it asks to pay."""
    name, deps = specialist.name, ctx.deps
    print(f"    boss → {name}: {task}")
    prompt = f"Ticket {deps.current_ticket_id}. Today is {deps.shop_date}. Task from the Boss: {task}"
    run_args = dict(deps=deps, usage=ctx.usage, usage_limits=ctx.usage_limits,
                    event_stream_handler=live_tool_calls(deps.audit, name, deps.current_ticket_id))
    deps.audit.append("agent_started", agent=name, ticket_id=deps.current_ticket_id, task=task, delegated_by="boss")
    started, approval_rounds = time.monotonic(), 0
    try:
        result = await specialist.run(prompt, **run_args)
        while isinstance(result.output, DeferredToolRequests):
            approval_rounds += 1
            approvals = await resolve_payment_approvals(result.output, deps)
            result = await specialist.run(
                message_history=result.all_messages(), deferred_tool_results=approvals, **run_args
            )
    except Exception as exc:
        deps.audit.append("agent_error", agent=name, ticket_id=deps.current_ticket_id, task=task,
                          error=f"{type(exc).__name__}: {exc}")
        raise
    deps.audit.agent_loop(name, deps.current_ticket_id, task, result, started,
                          delegated_by="boss", approval_rounds=approval_rounds)
    print(f"    {name} → boss: {result.output.summary}")
    return result.output


@boss_agent.tool
async def ask_inventory(ctx: RunContext[ShopDeps], task: str) -> InventoryReport:
    """Inventory: stock by SKU/size, stock issues, choosing a restock vendor, vendor lead times, vendor drafts."""
    return await delegate(ctx, inventory_agent, task)


@boss_agent.tool
async def ask_accounting(ctx: RunContext[ShopDeps], task: str) -> AccountingReport:
    """Accounting: cash, invoices, margins and discounts, purchase orders, and payments (human-approved)."""
    return await delegate(ctx, accounting_agent, task)


@boss_agent.tool
async def ask_facilities(ctx: RunContext[ShopDeps], task: str) -> FacilitiesReport:
    """Facilities: rent, leases, landlord, and the shop space."""
    return await delegate(ctx, facilities_agent, task)


@boss_agent.tool
async def ask_customer_service(ctx: RunContext[ShopDeps], task: str) -> CustomerServiceReport:
    """Customer service: drafts messages to customers. Tell it exactly what was decided."""
    return await delegate(ctx, customer_service_agent, task)
