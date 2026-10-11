# Campus Customs agent team (PydanticAI)

Five agents work the shop's open tickets using `gpt-6-luna` through Portkey (`PORTKEY_API_KEY` from `.env`).
**All shop data comes from the Campus Customs MCP server** (`mcp_server/server.py`), which talks to
`data/campus_customs_new.db`. No code in `backend/` opens the database.

| Agent | File | Prompt | Job |
|---|---|---|---|
| Boss | `boss.py` | `prompts/boss.md` | Reads each ticket, delegates to specialists, makes the final call |
| Inventory | `inventory.py` | `prompts/inventory.md` | Stock by SKU/size, stock issues, restock vendor and lead time |
| Accounting | `accounting.py` | `prompts/accounting.md` | Cash, invoices, margins, POs, human-approved payments |
| Facilities | `facilities.py` | `prompts/facilities.md` | Rent, leases, the shop space |
| Customer service | `customer_service.py` | `prompts/customer_service.md` | Drafts every customer message |

- `models.py`: data types (reports, decisions, payment previews and approvals, run-time deps)
- `config.py`: the model, the MCP connection, and `shop_tools()`, which gives each agent only its own MCP tools
- `audit.py`: the append-only audit trail
- `run.py`: the full run

## How they work together
- **Agent loops:** each agent runs PydanticAI's tool loop: it calls its MCP tools until it can return a typed report.
  `run.py` loops the Boss over every open ticket.
- **Delegation:** the Boss calls `ask_inventory`, `ask_accounting`, `ask_facilities`, and `ask_customer_service`.
  Each one runs that specialist's own loop. Specialists can request a colleague through `needs_help_from`.
- **Payments:** `pay` is wrapped with `approval_required`. When Accounting calls it, the run pauses, a payment
  request goes on the board, and the person at the terminal approves or denies it. Only then does the MCP `pay` run.
- **Audit:** every agent loop, tool call, approval, decision, and error is appended to `output/audit_trail.json`.
- **Board:** drafts go to `output/board.md`. Nothing is emailed or called.

The full tool list, which tables each tool uses, and the safety guardrails are in `output/harness.md`.

## Run it (from the Homework 5 folder)
```bash
.venv/bin/python -m backend.run
```
A full run always resets the database to the original values first (through the MCP tool `start_full_run`).
Answer `y` at a payment prompt to approve it. If no one is at the terminal, payments stay pending on the board.

## Desk API (`main.py`)
From the `backend/` folder, with the project's `.venv`:
```bash
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```
Interactive docs are at http://localhost:8000/docs, and the route list is in `output/harness.md`.
When agents run through the API, payments and POs wait on the board until a human calls
`POST /approvals/{id}/approve`. Only one ticket runs at a time.
