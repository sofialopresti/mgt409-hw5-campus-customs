# Campus Customs MCP Server

## What it is for
This is the shared toolbox for the Campus Customs multi-agent team: Boss, Inventory, Accounting, Facilities, and Customer Service. Every agent gets shop information **only** through these tools. No agent opens the database itself, so all agents see the same facts and every answer comes straight from the shop's data. Nothing is invented.

Built with [FastMCP](https://gofastmcp.com). The agents (`backend/`, PydanticAI) connect to it over stdio. Each agent is limited to the tools for its specialty.

## Database
- **Uses:** `data/campus_customs_new.db`, the working copy that agents update
- **Original:** `data/campus_customs.db`. It is never changed: it's only read for `get_inventory_change_tickets` comparisons and as the source for resets
- **Reset before a full run:** `backend/run.py` calls `start_full_run`, which copies the original over the working copy and clears the board. `python3 reset_db.py` does the same database reset by hand

"Today" for the shop is `desk.date_today` (2026-08-31). The tools use it for days until due, overdue status, and restock arrival dates. They never use the computer clock.

**The board** (`output/board.json` and `output/board.md`, managed by `board.py`) is where draft messages, POs, payment requests, and decisions go. Nothing on it is ever sent.

## Tools

### Ticket overview (from Problem 3)
| Tool | What it returns | Tables |
|---|---|---|
| `get_outgoing_payment_tickets(status="open")` | Tickets that need money to go **out**: vendor invoices and rent, with payee, amount, due date, and `days_until_due` (negative = overdue) | `tickets`, `invoices`, `vendors`, `leases`, `desk` |
| `get_incoming_payment_tickets(status="open")` | Tickets that would bring money **in** (SKU sales): `unit_cost`, `list_price`, sale value at list price, and gross margin | `tickets`, `pricing`, `desk` |
| `get_inventory_change_tickets(status="open")` | Each ticket's effect on stock (on hand, requested, shortfall), plus every SKU/size whose qty changed from the original database | `tickets`, `inventory`, `desk`, original `inventory` |

### Agent tools
| Tool | Agent | What it does | Reads | Writes |
|---|---|---|---|---|
| `get_ticket(ticket_id)` | Boss, Customer service | One ticket plus `date_today` | `tickets`, `desk` | none |
| `view_board(ticket_id=None)` | Boss | Drafts and decisions so far | board | none |
| `check_stock(sku, size, qty_requested)` | Inventory | On hand, shortfall, other sizes | `inventory` | none |
| `list_stock_issues()` | Inventory | Out of stock and low stock (qty 3 or less) | `inventory` | none |
| `list_vendors()` | Inventory | Specialty, `lead_days`, open invoices, `will_ship` | `vendors`, `invoices` | none |
| `quote_restock(vendor_id, sku, size, qty)` | Inventory | Cost, and arrival = today + `lead_days`; flags a blocked vendor | `vendors`, `pricing`, `invoices`, `desk` | none |
| `draft_vendor_message(ticket_id, vendor_id, subject, body)` | Inventory | Draft to a vendor (not sent) | `tickets`, `vendors`, `desk` | board |
| `get_cash_position(account)` | Accounting | Balance, open invoices, rent due within 30 days | `cash_accounts`, `invoices`, `leases`, `desk` | none |
| `list_invoices(status)` | Accounting | Invoices with days until due | `invoices`, `vendors`, `desk` | none |
| `check_margin(sku, qty, discount_pct)` | Accounting | Margin at a discount, below-cost flag, maximum discount | `pricing` | none |
| `preview_payment(kind, ref_id, account)` | Accounting | What a payment would do. Moves no money | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk` | none |
| `pay(kind, ref_id, ticket_id, ...)` | Accounting, **after human approval** | Pays an invoice or rent. Refuses without an approved board request or when cash is short | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, board | `cash_accounts`, `payments`, `invoices` or `leases`, board |
| `prepare_purchase_order(ticket_id, vendor_id, sku, size, qty, note)` | Accounting | Draft PO for a human to check. Blocked if the vendor has an unpaid invoice | `tickets`, `vendors`, `pricing`, `invoices`, `desk` | board |
| `list_leases()` / `get_lease(lease_id)` | Facilities | Rent, next due date, days until due | `leases`, `desk` | none |
| `draft_facilities_note(ticket_id, to, subject, body)` | Facilities | Draft to the landlord, etc. (not sent) | `tickets`, `desk` | board |
| `get_product(sku)` | Customer service | Name, list price, stock by size (no costs) | `inventory`, `pricing` | none |
| `draft_customer_message(ticket_id, to, subject, body)` | Customer service | Draft to a customer (not emailed) | `tickets`, `desk` | board |

### Run-loop and desk API tools (only `backend/run.py` and `backend/main.py` call these; no agent can see them)
| Tool | What it does | Reads | Writes |
|---|---|---|---|
| `list_tickets()` | Every ticket with its status | `tickets`, `desk` | none |
| `approve_purchase_order(purchase_order_id, approved_by)` | A human approves a draft PO. Refused while the vendor has an unpaid invoice | board, `invoices` | board |
| `start_full_run()` | Resets the working DB from the original and clears the board | original DB, `tickets`, `desk` | whole working DB, board |
| `request_payment_approval(ticket_id, kind, ref_id, account)` | Pins a payment request for the human. Reuses an existing one instead of duplicating | `tickets`, `cash_accounts`, `invoices`, `vendors`, `leases`, `desk`, board | board |
| `set_payment_request_status(payment_request_id, approved, approver, note)` | Records the human's decision | board | board |
| `record_ticket_decision(ticket_id, status, final_call, ...)` | Saves the Boss's final call | `tickets`, `desk` | `tickets.status`, board |

## Money rules the server enforces
- `pay` only works for a board payment request a human approved, with a matching invoice or lease. The approver's name is saved in `payments.approved_by`.
- It refuses when cash is short, when the invoice is already paid, or when rent is already paid through the next month.
- A successful payment updates `cash_accounts`, `payments`, and `invoices.status` (or `leases.next_due`) in one transaction.
- No tool ever adds cash. There is no revenue in this project.

See `output/harness.md` for the full safety section and the audit trail format.

## Run it
From the `Homework 5` folder:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python mcp_server/server.py
```

## Connection
- **Claude Code:** registered in `.mcp.json` at the project root as `campus-customs` (stdio, `.venv/bin/python mcp_server/server.py`).
- **The agent team:** `backend/config.py` launches the same script over stdio. Server logs go to `output/mcp_server.log`.

## Smoke test (Problem 4)
```bash
python3 reset_db.py
.venv/bin/python mcp_server/smoke_test.py
```
This launches the server from `.mcp.json`, calls the three ticket-overview tools, and checks each value against `data/campus_customs.db`. It writes the evidence to `output/mcp_smoke/<tool_name>.json`.
