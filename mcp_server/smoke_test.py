"""Smoke test for the Campus Customs MCP server.

Launches the server exactly as configured in .mcp.json (stdio), calls every
tool, and checks each returned value against the original database
data/campus_customs.db using independent SQL queries. Writes one evidence
file per tool to output/mcp_smoke/<tool_name>.json.

Run from the Homework 5 folder after a reset:
    python3 reset_db.py
    .venv/bin/python mcp_server/smoke_test.py
"""

import asyncio
import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

from fastmcp import Client

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"
OUT_DIR = ROOT / "output" / "mcp_smoke"

PROMPT_BUILD_SERVER = (
    "We are building an MPC server now in mpc_server/ use FastMCP and i want it to talk to "
    "data/campus_customs_new.bd. every agent will use the tools in this server. i want to add three "
    "tools to look at the tickets in the database. How about they are payment outgoing, payment incoming "
    "and type (so like, rent, inventory sale, etc.) , use only information from the database, dont invent. "
    "in harness.md list my tools and include what table it reads, what ticket it unlocks and a single "
    "sentence on why the tool is right for the ticket, and make it specific to the ticket. add "
    "mcp_server/README.md to explain what the mcp server is for, the database file it uses and the three "
    "tools it has"
)
PROMPT_INVENTORY_TOOL = (
    "can you change ticket 3 from get tickets by type to inventory change, and make it track inventory "
    "changes and if a ticket alters that"
)


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(f"file:{ORIGINAL_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, params)]
    conn.close()
    return rows


def check(checks: list, label: str, tool_value, db_value, source: str) -> None:
    checks.append({
        "check": label,
        "tool_value": tool_value,
        "db_value": db_value,
        "db_source": source,
        "match": tool_value == db_value,
    })


def verify_outgoing(out: dict) -> list:
    checks = []
    today = query("SELECT date_today FROM desk")[0]["date_today"]
    check(checks, "date_today", out["date_today"], today, "desk.date_today")

    expected = query("SELECT id FROM tickets WHERE status='open' AND (invoice_id IS NOT NULL OR lease_id IS NOT NULL) ORDER BY id")
    check(checks, "outgoing ticket ids", [t["ticket_id"] for t in out["tickets"]], [r["id"] for r in expected],
          "tickets WHERE invoice_id OR lease_id IS NOT NULL")

    total = 0.0
    for t in out["tickets"]:
        for o in t["outgoing"]:
            if o["kind"] == "vendor_invoice":
                row = query("SELECT i.amount, i.due_date, i.status, v.name FROM invoices i JOIN vendors v ON v.id=i.vendor_id WHERE i.id=?", (o["invoice_id"],))[0]
                src = f"invoices.id={o['invoice_id']} JOIN vendors"
                check(checks, f"ticket {t['ticket_id']} invoice amount", o["amount"], row["amount"], src)
                check(checks, f"ticket {t['ticket_id']} invoice due_date", o["due_date"], row["due_date"], src)
                check(checks, f"ticket {t['ticket_id']} invoice status", o["invoice_status"], row["status"], src)
                check(checks, f"ticket {t['ticket_id']} pay_to vendor", o["pay_to"], row["name"], src)
                due = row["due_date"]
            else:
                row = query("SELECT monthly_rent, next_due, landlord FROM leases WHERE id=?", (o["lease_id"],))[0]
                src = f"leases.id={o['lease_id']}"
                check(checks, f"ticket {t['ticket_id']} rent amount", o["amount"], row["monthly_rent"], src)
                check(checks, f"ticket {t['ticket_id']} rent due_date", o["due_date"], row["next_due"], src)
                check(checks, f"ticket {t['ticket_id']} pay_to landlord", o["pay_to"], row["landlord"], src)
                due = row["next_due"]
            check(checks, f"ticket {t['ticket_id']} days_until_due", o["days_until_due"],
                  (date.fromisoformat(due) - date.fromisoformat(today)).days, "due_date - desk.date_today")
            total += o["amount"]
    check(checks, "total_outgoing", out["total_outgoing"], total, "sum of invoice + rent amounts above")
    return checks


def verify_incoming(out: dict) -> list:
    checks = []
    expected = query("SELECT t.id, t.qty, p.unit_cost, p.list_price FROM tickets t JOIN pricing p ON p.sku=t.sku WHERE t.status='open' AND t.sku IS NOT NULL ORDER BY t.id")
    check(checks, "incoming ticket ids", [t["ticket_id"] for t in out["tickets"]], [r["id"] for r in expected],
          "tickets WHERE sku IS NOT NULL")
    by_id = {r["id"]: r for r in expected}
    for t in out["tickets"]:
        r = by_id[t["ticket_id"]]
        src = f"tickets.id={t['ticket_id']} JOIN pricing"
        check(checks, f"ticket {t['ticket_id']} qty", t["qty"], r["qty"], src)
        check(checks, f"ticket {t['ticket_id']} unit_cost", t["unit_cost"], r["unit_cost"], src)
        check(checks, f"ticket {t['ticket_id']} list_price", t["list_price"], r["list_price"], src)
        check(checks, f"ticket {t['ticket_id']} sale_value_at_list", t["sale_value_at_list"], r["list_price"] * r["qty"], "list_price x qty")
        check(checks, f"ticket {t['ticket_id']} total_cost", t["total_cost"], r["unit_cost"] * r["qty"], "unit_cost x qty")
        check(checks, f"ticket {t['ticket_id']} gross_margin_at_list", t["gross_margin_at_list"],
              (r["list_price"] - r["unit_cost"]) * r["qty"], "(list_price - unit_cost) x qty")
    check(checks, "total_sale_value_at_list", out["total_sale_value_at_list"],
          sum(r["list_price"] * r["qty"] for r in expected), "sum of list_price x qty")
    return checks


def verify_inventory(out: dict) -> list:
    checks = []
    for t in out["ticket_impacts"]:
        r = query("SELECT t.qty AS requested, i.qty AS on_hand, i.name, i.location FROM tickets t JOIN inventory i ON i.sku=t.sku AND i.size=t.size WHERE t.id=?", (t["ticket_id"],))[0]
        src = f"tickets.id={t['ticket_id']} JOIN inventory ({t['sku']}, {t['size']})"
        check(checks, f"ticket {t['ticket_id']} qty_on_hand", t["qty_on_hand"], r["on_hand"], src)
        check(checks, f"ticket {t['ticket_id']} qty_requested", t["qty_requested"], r["requested"], src)
        check(checks, f"ticket {t['ticket_id']} item_name", t["item_name"], r["name"], src)
        check(checks, f"ticket {t['ticket_id']} location", t["location"], r["location"], src)
        check(checks, f"ticket {t['ticket_id']} shortfall", t["shortfall"], max(r["requested"] - r["on_hand"], 0), "max(requested - on_hand, 0)")
    no_sku = query("SELECT id FROM tickets WHERE status='open' AND sku IS NULL ORDER BY id")
    check(checks, "tickets not altering inventory", [t["ticket_id"] for t in out["tickets_not_altering_inventory"]],
          [r["id"] for r in no_sku], "tickets WHERE sku IS NULL")
    check(checks, "changes_since_original (working copy freshly reset)", out["changes_since_original"], [],
          "inventory in campus_customs_new.db vs campus_customs.db")
    return checks


TOOLS = [
    ("get_outgoing_payment_tickets", PROMPT_BUILD_SERVER, verify_outgoing),
    ("get_incoming_payment_tickets", PROMPT_BUILD_SERVER, verify_incoming),
    ("get_inventory_change_tickets", PROMPT_INVENTORY_TOOL, verify_inventory),
]


async def main() -> None:
    config = json.loads((ROOT / ".mcp.json").read_text())
    for server in config["mcpServers"].values():
        server["cwd"] = str(ROOT)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    async with Client(config) as client:
        listed = sorted(t.name for t in await client.list_tools())
        for name, prompt, verify in TOOLS:
            result = await client.call_tool(name, {})
            checks = verify(result.data)
            evidence = {
                "prompt_to_vibe_coder": prompt,
                "tool_name": name,
                "arguments": {},
                "server": "campus-customs (launched from .mcp.json over stdio)",
                "tools_listed_by_server": listed,
                "ran_at": datetime.now().isoformat(timespec="seconds"),
                "database_queried_by_tool": "data/campus_customs_new.db",
                "database_verified_against": "data/campus_customs.db",
                "tool_output": result.data,
                "verification": {
                    "all_match": all(c["match"] for c in checks),
                    "checks_passed": sum(c["match"] for c in checks),
                    "checks_total": len(checks),
                    "checks": checks,
                },
            }
            path = OUT_DIR / f"{name}.json"
            path.write_text(json.dumps(evidence, indent=2) + "\n")
            v = evidence["verification"]
            print(f"{name}: {v['checks_passed']}/{v['checks_total']} checks match -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
