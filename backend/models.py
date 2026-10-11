"""Data types shared by the Campus Customs agent team.

Payment previews and approvals, agent reports, the Boss's final decision, and
the run-time dependencies (the human approver and the audit trail) live here.
Shop data itself comes from the MCP server's tools.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .audit import AuditTrail

SpecialistName = Literal["inventory", "accounting", "facilities", "customer_service"]
TicketStatus = Literal["resolved", "waiting_on_restock", "waiting_on_human", "blocked"]
PaymentKind = Literal["invoice", "rent"]


# ---------------------------------------------------------------- payments

class PaymentPreview(BaseModel):
    """What a payment would do (from the MCP preview), shown to the human before they approve it."""

    kind: PaymentKind
    ref_id: int
    payee: str | None = None
    description: str | None = None
    amount: float = 0
    account: str
    cash_before: float = 0
    cash_after: float = 0
    can_afford: bool = False
    problem: str | None = None
    ticket_id: int | None = None


class ApprovalDecision(BaseModel):
    approved: bool
    approver: str = ""
    note: str = ""


# ---------------------------------------------------------------- agent outputs

class HelpRequest(BaseModel):
    """A specialist asking the Boss to bring in a colleague."""

    agent: SpecialistName
    request: str


class SpecialistReport(BaseModel):
    ticket_id: int
    summary: str = Field(description="One or two sentences the Boss can act on.")
    findings: list[str] = Field(description="Facts from the database, with numbers.")
    actions_taken: list[str] = Field(description="Tool actions taken (drafts, POs, payments). Empty if none.")
    recommendations: list[str]
    needs_help_from: list[HelpRequest] = Field(default_factory=list)


class InventoryReport(SpecialistReport):
    can_fill_now: bool | None = None
    shortfall: int = 0
    recommended_vendor: str | None = None
    expected_arrival: str | None = None
    restock_blocked_reason: str | None = None


class AccountingReport(SpecialistReport):
    cash_balance: float | None = None
    margin_ok: bool | None = None


class FacilitiesReport(SpecialistReport):
    lease_id: int | None = None
    rent_amount: float | None = None
    rent_due: str | None = None
    days_until_due: int | None = None


class CustomerServiceReport(SpecialistReport):
    draft_ids: list[int] = Field(default_factory=list, description="Board ids of the drafts written.")


class TicketDecision(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    agents_consulted: list[SpecialistName]
    final_call: str = Field(description="The decision in plain language, with the key numbers.")
    status: TicketStatus
    human_follow_ups: list[str] = Field(description="What a person at the shop still needs to do.")


# ---------------------------------------------------------------- run-time dependencies

Approver = Callable[[PaymentPreview], ApprovalDecision]


@dataclass
class ShopDeps:
    approver: Approver
    audit: AuditTrail
    shop_date: str
    current_ticket_id: int | None = None


# ---------------------------------------------------------------- desk API (backend/main.py)

class TicketView(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    status: str = Field(description="Exact tickets.status, e.g. open, resolved, waiting_on_human.")
    state: Literal["resolved", "open"] = Field(
        description="'open' until the agents have worked the ticket, then 'resolved'; see status for the outcome."
    )
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    notes: str | None = None
    created_at: str


class RunStatus(BaseModel):
    run_id: str
    ticket_id: int
    state: Literal["running", "finished", "failed"]
    started_at: str
    finished_at: str | None = None
    decision: TicketDecision | None = None
    error: str | None = None


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human clicking Approve.")


class AgentEvent(BaseModel):
    """One audit-trail entry, trimmed for the board."""

    seq: int
    run_id: str
    logged_at: str
    event: str
    agent: str | None = None
    ticket_id: int | None = None
    summary: str | None = None
    tools_used: list[str] = Field(default_factory=list)
    tool_calls: list[dict] = Field(default_factory=list)
    detail: dict | None = Field(None, description="The agent's typed output, the Boss's decision, or a payment result.")
