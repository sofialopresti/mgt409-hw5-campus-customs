# Harness — Campus Customs

How the Campus Customs agent system fits together, in five parts:
1. **Tables:** the shop database.
2. **MCP tools:** the only way agents reach that data.
3. **The five agents.**
4. **The desk API routes.**
5. **The React dashboard and its safety rules.**

Results of the latest full run are at the end.

```
React dashboard (frontend/, :5173) ──HTTP──▶ Desk API (backend/main.py, :8000) ──▶ Boss + 4 agents (PydanticAI, gpt-6-luna via Portkey)
                                                        │                                   │
                                                        └──────────── MCP (stdio) ──────────┴──▶ mcp_server/server.py ──▶ data/campus_customs_new.db
```

## Tables

Working copy: `data/campus_customs_new.db`. The original, `data/campus_customs.db`, is never changed. Reset with
`POST /reset`, a full `python -m backend.run`, or `python3 reset_db.py`. The reset copies the original over the
working copy; all three do the same database reset.

| Table | Key fields | Why it matters for the agents |
|---|---|---|
| `desk` | `date_today`, `notes` | Defines "today" (2026-08-31) so agents can tell what is overdue or coming due. |
| `tickets` | `id`, `type`, `requester`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status` | The work queue — Boss reads each open ticket and routes it to the right agent. |
| `inventory` | `sku`, `size`, `qty`, `location` | Lets Inventory check stock by SKU and size and spot shortfalls before promising an order. |
| `pricing` | `sku`, `unit_cost`, `list_price` | Lets Accounting check margins so discounts never sell below cost. |
| `vendors` | `id`, `name`, `specialty`, `lead_days` | Tells Inventory which vendor can restock an item and how many days it will take. |
| `leases` | `id`, `space_name`, `landlord`, `monthly_rent`, `next_due` | Gives Facilities the rent amount and due date for the shop space. |
| `cash_accounts` | `name`, `balance`, `date` | The money available — the pay tool must refuse any payment that would go negative. |
| `invoices` | `id`, `vendor_id`, `amount`, `due_date`, `status` | Shows unpaid vendor bills; a vendor with an open invoice will not ship new product. |
| `payments` | `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by` | The audit log of human-approved payments; must be updated whenever a payment is made. |

## Problem 3 ticket tools (`mcp_server/server.py`)

The three original ticket-overview tools. They read `data/campus_customs_new.db` and are read-only.
The full list of MCP tools is further down.

| Tool | Tables read | Ticket it unlocks | Why it is right for this ticket |
|---|---|---|---|
| `get_outgoing_payment_tickets` | `tickets`, `invoices`, `vendors`, `leases`, `desk` | 101 (Bulldog tee) | It shows invoice 501 owes Bulldog Print Co $840 and is 3 days overdue, the bill blocking the restock of the out-of-stock size S tee. |
| `get_outgoing_payment_tickets` | `tickets`, `invoices`, `vendors`, `leases`, `desk` | 102 (Rent due) | It pulls the $2,400 Chapel Street rent owed to Elm City Properties and shows it is due in 2 days (2026-09-02). |
| `get_incoming_payment_tickets` | `tickets`, `pricing`, `desk` | 101 (Bulldog tee) | It values Tauhid Zaman's 1 size S tee at the $28 list price against an $8 cost, so the team knows what the sale is worth. |
| `get_incoming_payment_tickets` | `tickets`, `pricing`, `desk` | 103 (Bulk hoodie discount) | It shows the Yale AI Club's 20 size M hoodies are worth $1,160 at list against a $440 cost, the $720 margin any bulk discount has to come out of. |
| `get_inventory_change_tickets` | `tickets`, `inventory`, `desk` (+ original `inventory` for comparison) | 101 (Bulldog tee) | It shows the Classic Bulldog Tee in size S has 0 on hand against 1 requested, so filling Tauhid's order needs a restock first. |
| `get_inventory_change_tickets` | `tickets`, `inventory`, `desk` (+ original `inventory` for comparison) | 103 (Bulk hoodie discount) | It shows only 8 size M hoodies are on hand against the Yale AI Club's 20, a 12-unit shortfall to cover before any discount is offered. |
| `get_inventory_change_tickets` | `tickets`, `inventory`, `desk` (+ original `inventory` for comparison) | 102 (Rent due) | It confirms the rent notice does not alter inventory, so the stock check can skip it. |

## The five agents (`backend/`, PydanticAI, `gpt-6-luna` via Portkey)

Agents get shop data **only** through the Campus Customs MCP server. No agent code opens the database.
Each agent is limited to the MCP tools listed for it.

| Agent | File / prompt | Job | MCP tools it can use |
|---|---|---|---|
| Boss | `backend/boss.py` / `prompts/boss.md` | Reads each ticket, delegates to specialists (`ask_*`), makes the final call | `get_ticket`, `view_board`, `get_outgoing_payment_tickets`, `get_incoming_payment_tickets`, `get_inventory_change_tickets` |
| Inventory | `backend/inventory.py` / `prompts/inventory.md` | Stock by SKU/size, stock issues, restock vendor and lead time | `check_stock`, `list_stock_issues`, `list_vendors`, `quote_restock`, `draft_vendor_message`, `get_inventory_change_tickets` |
| Accounting | `backend/accounting.py` / `prompts/accounting.md` | Cash, invoices, margins, POs, human-approved payments | `get_cash_position`, `list_invoices`, `check_margin`, `preview_payment`, `pay` (human approval), `prepare_purchase_order`, `get_outgoing_payment_tickets`, `get_incoming_payment_tickets` |
| Facilities | `backend/facilities.py` / `prompts/facilities.md` | Rent, leases, the shop space | `list_leases`, `get_lease`, `draft_facilities_note` |
| Customer service | `backend/customer_service.py` / `prompts/customer_service.md` | Drafts every customer message | `get_ticket`, `get_product`, `draft_customer_message` |
| Run loop + desk API (not agents) | `backend/run.py`, `backend/main.py` | Reset the database, run the Boss on tickets, handle human approvals | `list_tickets`, `approve_purchase_order`, `start_full_run`, `request_payment_approval`, `set_payment_request_status`, `record_ticket_decision` (plus `view_board`, `get_cash_position`, `pay` after a human approves) |

## All MCP tools and the tables they use (`mcp_server/server.py`)

"Board" means `output/board.json` / `board.md`: drafts only, never sent.

| MCP tool | Used by | Reads | Writes |
|---|---|---|---|
| `get_outgoing_payment_tickets` | Boss, Accounting | `tickets`, `invoices`, `vendors`, `leases`, `desk` | none |
| `get_incoming_payment_tickets` | Boss, Accounting | `tickets`, `pricing`, `desk` | none |
| `get_inventory_change_tickets` | Boss, Inventory | `tickets`, `inventory`, `desk`, original `inventory` | none |
| `get_ticket` | Boss, Customer service | `tickets`, `desk` | none |
| `view_board` | Boss | board | none |
| `check_stock` | Inventory | `inventory` | none |
| `list_stock_issues` | Inventory | `inventory` | none |
| `list_vendors` | Inventory | `vendors`, `invoices` | none |
| `quote_restock` | Inventory | `vendors`, `pricing`, `invoices`, `desk` | none |
| `draft_vendor_message` | Inventory | `tickets`, `vendors`, `desk` | board |
| `get_cash_position` | Accounting | `cash_accounts`, `invoices`, `leases`, `desk` | none |
| `list_invoices` | Accounting | `invoices`, `vendors`, `desk` | none |
| `check_margin` | Accounting | `pricing` | none |
| `preview_payment` | Accounting | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk` | none |
| `pay` | Accounting (only after human approval) | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, board | `cash_accounts`, `payments`, `invoices` or `leases`, board |
| `prepare_purchase_order` | Accounting | `tickets`, `vendors`, `pricing`, `invoices`, `desk` | board |
| `list_leases` | Facilities | `leases`, `desk` | none |
| `get_lease` | Facilities | `leases`, `desk` | none |
| `draft_facilities_note` | Facilities | `tickets`, `desk` | board |
| `get_product` | Customer service | `inventory`, `pricing` | none |
| `draft_customer_message` | Customer service | `tickets`, `desk` | board |
| `list_tickets` | Run loop / API only | `tickets`, `desk` | none |
| `approve_purchase_order` | API only (human click) | board, `invoices` | board |
| `start_full_run` | Run loop / API only | `campus_customs.db` (original), `tickets`, `desk` | whole working DB (reset), board (cleared) |
| `request_payment_approval` | Run loop only | `tickets`, `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, board | board |
| `set_payment_request_status` | Run loop only | board | board |
| `record_ticket_decision` | Run loop only | `tickets`, `desk` | `tickets.status`, board |

## Desk API routes (`backend/main.py`, FastAPI on http://localhost:8000)

- `GET /tickets`: returns the three tickets and whether each is resolved (the agents finished it) or open, plus the Boss's exact status.
- `POST /tickets/{ticket_id}/run`: starts the agent team on one ticket in the background, and returns a `run_id`.
- `GET /runs/{run_id}`: shows whether that ticket run is still running, and the Boss's final call once it's done.
- `GET /events?limit=&ticket_id=&since_seq=`: returns recent agent events from the audit trail (what each agent did and the MCP tools it used), so the board can refresh.
- `GET /approvals`: lists payment requests and purchase orders on the board that are waiting for a human.
- `POST /approvals/{item_id}/approve`: a human clicks Approve (body `{"approved_by": "name"}`). It pays the payment request, or approves the PO; agents only prepare these.
- `GET /cash`: returns the checking balance from `cash_accounts`.
- `POST /reset`: resets the working database to the original values and clears the board, for a fresh run.

## Dashboard (`frontend/`, React + Vite + TypeScript, http://localhost:5173)

Start it with `npm run dev` in `frontend/`. The backend must already be running on :8000, and it allows only
this origin (CORS). The design rationale is in `output/design.md`.

| Part of the board | What it shows | API route it calls |
|---|---|---|
| Desk tickets | The three tickets. Each gets a RESOLVED stamp and the Boss's outcome once the team finishes it | `GET /tickets` |
| Start the agent team | Runs the team on the selected ticket. Disabled while another ticket is running | `POST /tickets/{id}/run` |
| Agent team | The Boss and four agents as cartoon characters: idle, working (with a speech bubble from each live tool call), or done | `GET /events` (polled) |
| What the team did | The Boss's final call, one line per agent, and the human follow-ups | `GET /events` |
| Activity | Every step, with the agent's face and the exact MCP tool and arguments | `GET /events?since_seq=` |
| Checking | The balance from `cash_accounts`. It counts down after an approved payment, with a step chart and a ledger | `GET /cash` |
| Needs your OK | Payment requests and POs that agents prepared, each with an Approve button | `GET /approvals`, `POST /approvals/{id}/approve` |
| Fresh run (reset) | Resets the database and board after a confirmation | `POST /reset` |

## Dashboard safety rules
- **The dashboard can't move money by itself.** Only `POST /approvals/{id}/approve` moves money, and it needs a
  typed approver name. Agents only *prepare* payments and POs.
- **The server enforces the money rules, not the browser.** Even if someone edited the page, `pay` still
  refuses a payment with no matching approved request, a short balance, or an invoice or rent already paid.
  `approve_purchase_order` refuses while the vendor has an unpaid invoice. For example, my first click on
  PO #1 before invoice 501 was paid was refused (audit seq 197).
- **Only one ticket runs at a time.** Approvals and resets are locked while agents are working (409 errors),
  so money can't change under a running agent.
- **Resets need confirmation,** and the audit trail is never wiped.
- **Refusals stay visible.** If the server refuses an approval, the reason shows on the card instead of
  quietly failing.
- **Only the local board can call the API.** The backend accepts browser calls from localhost pages only,
  never from other websites.
- **Nothing is sent from the dashboard.** Drafts to customers, vendors, and the landlord stay on the board
  for a person to send.
- **Agents always get fresh answers.** Agent calls skip Portkey's response cache, so they never act on a
  stale cached answer. (A cached tool call caused one failed run of ticket 102.)
- **Saving code can interrupt a run.** Don't save backend `.py` files while a ticket is running:
  `uvicorn --reload` restarts the server and stops the run. One interrupted run of 102 is recorded in the
  audit trail.

## Audit trail (`output/audit_trail.json`)

Each event is appended as it happens. The file is never wiped, and each run gets its own `run_id`.
- `run_started` / `run_finished`: model, shop date, open tickets, and the outcome for each ticket.
- `agent_started` and `tool_call`: logged live, the moment an agent gets a task or calls an MCP tool,
  so the board can show who is working and what they are doing.
- `agent_loop` (one per agent loop): agent, ticket, task given, every MCP tool call with its args and
  full result, typed output, model turns, token usage, duration, and who delegated it.
- `payment_approval`, `payment_refused_before_approval`, `payment_duplicate_blocked`: the payment
  preview, the human's decision and name, and the board request id.
- `ticket_decision`, `agent_error`.
- From the desk API: `payment_result`, `purchase_order_approval`, `purchase_order_refused`, `database_reset`
  (with `source: desk_api` and the approver's name).

## Safety guardrails for real money and real customers

**What this project already enforces**
- **A human approves every payment.** This is enforced in the MCP server, not just the prompt: `pay`
  refuses without an approved, matching board request, and the approver's name comes from the
  approval step, never from the model.
- **The server checks money rules.** It refuses when cash is short, when an invoice is already paid,
  when rent is already paid, and when the same payment is requested twice. Cash never goes up.
- **Each agent has only the tools it needs.** Payments, resets, and decision tools are hidden from
  the agents.
- **Nothing is sent.** Customer, vendor, and landlord messages are drafts until a person sends them.
  Customer drafts never show costs, margins, or vendor problems.
- **No invented facts.** Every number comes from an MCP tool, and the date is always `desk.date_today`.
- **Prices stay above cost.** `check_margin` flags anything below unit cost.
- **Everything is auditable.** The audit trail is append-only, and failures leave the ticket open.
  Each ticket is capped at 60 model requests.
- **The API key stays secret.** It is read only from `.env` and never logged.

**What a real business should add before going live**
- **Verified approvers.** Log approvers in with real accounts (SSO) instead of a typed name, and
  require two people for payments above a threshold, with daily limits.
- **Lock down the payment tools.** Production should have no `start_full_run` reset. Only the
  orchestrator should be able to call `pay`, through an authenticated MCP connection. Right now
  `.mcp.json` also exposes the write tools to the coding assistant.
- **Protect the audit trail.** Store it somewhere tamper-evident and back it up. Limit who can read
  it, since it contains customer names, and keep only the customer data you need.
- **Review pricing and outgoing messages.** Have a person sign off on discounts above a set percentage
  or on large orders. Review drafts before sending, and keep an opt-out list.
- **Test changes safely.** Test new prompts and tools against a copy of the data before they touch
  real money.

## Latest full run (2026-10-11, shop date 2026-08-31)

1. **Reset.** The database was reset through `POST /reset` (audit seq 94).
2. **Agent runs.** Tickets 101, 103 and 102 were run one at a time through the API.
3. **Approvals.** I (Sofia Lopresti) approved the payments and POs on the dashboard.

| Ticket | Boss status | Board | Human approvals | Cash |
|---|---|---|---|---|
| 101 Bulldog tee | waiting_on_human | Resolved | Paid invoice 501 ($840.00); PO #1 approved ($8.00) | −$840.00 |
| 102 Rent due | waiting_on_human | Resolved | Paid lease 1 rent ($2,400.00) | −$2,400.00 |
| 103 Bulk hoodie discount | waiting_on_human | Resolved | PO #5 approved ($264.00) | $0.00 |

- **Cash:** checking went from $3,400.00 to **$160.00**, which matches `cash_accounts` in the working database.
- **Why every ticket says waiting_on_human:** the Boss recorded each status before my approvals.
- **Write-ups:** details are in `output/resolved_tickets.json`, `output/desk_tickets.html` (Actual and Cash tabs),
  and `output/resolved_board.html` (dashboard screenshots).
