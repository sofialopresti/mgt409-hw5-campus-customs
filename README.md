# Campus Customs — AI Agent Team (MGT 409, Homework 5)

A five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service) that works the shop's desk tickets.
- **Backend:** PydanticAI agents using `gpt-6-luna` through Portkey, served by a FastAPI desk API.
- **Shop data:** the agents read and write it only through a FastMCP server, which talks to a SQLite database.
- **Board:** a React dashboard where a human watches the agents work and approves every payment and purchase order.

```
React board (frontend/, :5173) ──▶ FastAPI desk API (backend/main.py, :8000) ──▶ PydanticAI agents (backend/)
                                                                                   │
                                          MCP server (mcp_server/server.py) ◀──────┘──▶ data/campus_customs_new.db
```

## Requirements
- Python 3.12+ (built with 3.14) and Node.js 20+ (built with 24)
- A Portkey API key with access to `gpt-6-luna`

## 1. Setup (once)
Run these from the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then open .env and paste your PORTKEY_API_KEY
(cd frontend && npm install)
```

`.env` is git-ignored. Never commit a real key.

## 2. Copy the original database to the working copy (whenever you want a clean run)
`data/campus_customs.db` is the **original** shop data and is never changed.
`data/campus_customs_new.db` is the **working copy** that the agents update.

To start clean, copy the original over the working copy:

```bash
python3 reset_db.py           # same as: cp data/campus_customs.db data/campus_customs_new.db
```

The working copy in this repo is the state after my graded run (checking $160.00). Reset it before running again.

## 3. Start the MCP server
```bash
.venv/bin/python mcp_server/server.py
```

The MCP server (`campus-customs`, FastMCP over stdio) is the only way agents reach shop data. You don't need to
keep it running in its own terminal for the app:
- **The backend** launches its own copy automatically over stdio when it starts.
- **Claude Code / vibe coders** get it from `.mcp.json`, which registers it as `campus-customs`.

Run the command above to check the server starts (stop it with Ctrl+C). The tools are documented in
`mcp_server/README.md`.

## 4. Start the FastAPI backend (terminal 1)
```bash
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

Wait for `Application startup complete.` The API docs are at http://localhost:8000/docs.

## 5. Start the React board (terminal 2)
```bash
cd frontend
npm run dev
```

Open http://localhost:5173. The board must run on port 5173, because that is the origin the backend allows (CORS).

## 6. Reset the database before a full three-ticket run
Always reset before working all three tickets, so the run starts from the original data. Any of these works:
- **On the board:** click **Fresh run (reset)** at the top right.
- **Through the API:** `curl -X POST http://localhost:8000/reset`
- **From the terminal:** `python3 reset_db.py` (database only; it doesn't clear the board)

Then run the tickets.

**On the board:**
1. Pick ticket 101, click **Start the agent team**, and wait until the team is done.
2. Do the same for 102 and 103. Only one ticket runs at a time.
3. Type your name under **Needs your OK** and approve the payments and purchase orders. Approve the $840
   invoice payment before the purchase orders; the vendor won't ship until it's paid.

**Or from the terminal** (this resets the database itself and asks at the terminal before each payment):

```bash
.venv/bin/python -m backend.run
```

Don't save backend `.py` files while a ticket is running. `uvicorn --reload` restarts the server and cuts off the run.

## Repo layout
| Path | What it is |
|---|---|
| `AI_prompts.md` | The prompts I gave the vibe coder for each problem |
| `data/` | `campus_customs.db` (original) and `campus_customs_new.db` (working copy) |
| `mcp_server/` | `server.py` (FastMCP tools), `README.md`, `board.py` (draft board), `smoke_test.py` (Problem 4) |
| `backend/` | `main.py` (FastAPI routes), `models.py` (data types), `prompts/` (one prompt per agent), the five agent files, `run.py` (full CLI run), `audit.py`, `config.py` |
| `frontend/` | The React + Vite + TypeScript board |
| `output/harness.md` | Tables, MCP tools, the five agents, API routes, dashboard safety rules |
| `output/mcp_smoke.json` | Problem 4 evidence: each MCP tool's output checked against the database |
| `output/desk_tickets.html` | Expected vs. Actual per ticket, the itemized Cash tab, and my Reflection (double-click to open) |
| `output/design.md` | Dashboard design decisions |
| `output/resolved_tickets.json` | Final status, outcome, agent contributions, and human approvals for each ticket |
| `output/resolved_board.html` | Screenshots of the board for each resolved ticket (double-click to open) |
| `output/audit_trail.json` | Append-only log of every agent loop, tool call, approval, and reset |
| `output/github_url.txt` | This repo's URL |

## Safety rules (short version)
- **Human approval for money:** every payment needs a human to approve it, and the MCP server refuses `pay` without it. It also refuses when cash is short.
- **Vendor holds:** a vendor with an unpaid invoice won't ship, so its purchase orders stay blocked.
- **Drafts only:** agents never email customers or call vendors. Drafts stay on the board for a person to send.
- **The shop's "today"** is always `desk.date_today` (2026-08-31). Cash only goes out; no revenue is recorded.

The full guardrails are in `output/harness.md`.
