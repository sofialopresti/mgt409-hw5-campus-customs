"""Campus Customs MCP server — shared tools for every agent on the team.

All data comes from data/campus_customs_new.db (the working copy); the
original data/campus_customs.db is only read (for comparison, and as the
source for start_full_run's reset). Nothing is invented: every value
returned is read from, or computed directly from, rows in the database.

Agents never touch the database directly. Every read and write they make
goes through a tool here. Drafts go on the board (output/board.json),
which this server also owns.
"""

import calendar
import shutil
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

import board

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs_new.db"
ORIGINAL_DB_PATH = DATA_DIR / "campus_customs.db"

mcp = FastMCP("Campus Customs")


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run reset_db.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_date_today(conn: sqlite3.Connection) -> str:
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


@mcp.tool
def get_outgoing_payment_tickets(status: str = "open") -> dict:
    """List tickets that would require money to go OUT of the shop.

    A ticket is outgoing when it points to a vendor invoice (invoice_id) or a
    lease (lease_id). Returns the amount owed, who it is owed to, the due
    date, and days until due (negative = overdue) based on desk.date_today.
    """
    with get_connection() as conn:
        today = get_date_today(conn)
        rows = conn.execute(
            """
            SELECT t.id AS ticket_id, t.type, t.requester, t.subject, t.status AS ticket_status,
                   i.id AS invoice_id, i.amount AS invoice_amount, i.due_date AS invoice_due,
                   i.status AS invoice_status, i.description AS invoice_description,
                   v.name AS vendor_name,
                   l.id AS lease_id, l.space_name, l.landlord, l.monthly_rent, l.next_due AS rent_due
            FROM tickets t
            LEFT JOIN invoices i ON i.id = t.invoice_id
            LEFT JOIN vendors v ON v.id = i.vendor_id
            LEFT JOIN leases l ON l.id = t.lease_id
            WHERE t.status = ? AND (t.invoice_id IS NOT NULL OR t.lease_id IS NOT NULL)
            ORDER BY t.id
            """,
            (status,),
        ).fetchall()

    tickets = []
    for r in rows:
        obligations = []
        if r["invoice_id"] is not None:
            obligations.append({
                "kind": "vendor_invoice",
                "invoice_id": r["invoice_id"],
                "pay_to": r["vendor_name"],
                "amount": r["invoice_amount"],
                "due_date": r["invoice_due"],
                "days_until_due": days_between(today, r["invoice_due"]),
                "invoice_status": r["invoice_status"],
                "description": r["invoice_description"],
            })
        if r["lease_id"] is not None:
            obligations.append({
                "kind": "rent",
                "lease_id": r["lease_id"],
                "pay_to": r["landlord"],
                "space_name": r["space_name"],
                "amount": r["monthly_rent"],
                "due_date": r["rent_due"],
                "days_until_due": days_between(today, r["rent_due"]),
            })
        tickets.append({
            "ticket_id": r["ticket_id"],
            "type": r["type"],
            "requester": r["requester"],
            "subject": r["subject"],
            "status": r["ticket_status"],
            "outgoing": obligations,
        })

    return {
        "date_today": today,
        "ticket_status_filter": status,
        "total_outgoing": sum(o["amount"] for t in tickets for o in t["outgoing"]),
        "tickets": tickets,
    }


@mcp.tool
def get_incoming_payment_tickets(status: str = "open") -> dict:
    """List tickets that would bring money IN to the shop (sales of a SKU).

    A ticket is incoming when it requests a product (sku + qty). Values come
    from the pricing table: list_price x qty is the sale value at full price,
    unit_cost x qty is the cost. No discounts are assumed.
    """
    with get_connection() as conn:
        today = get_date_today(conn)
        rows = conn.execute(
            """
            SELECT t.id AS ticket_id, t.type, t.requester, t.subject, t.sku, t.size, t.qty,
                   t.status, t.notes, p.unit_cost, p.list_price
            FROM tickets t
            LEFT JOIN pricing p ON p.sku = t.sku
            WHERE t.status = ? AND t.sku IS NOT NULL AND t.qty IS NOT NULL
            ORDER BY t.id
            """,
            (status,),
        ).fetchall()

    tickets = []
    for r in rows:
        has_price = r["list_price"] is not None
        tickets.append({
            "ticket_id": r["ticket_id"],
            "type": r["type"],
            "requester": r["requester"],
            "subject": r["subject"],
            "sku": r["sku"],
            "size": r["size"],
            "qty": r["qty"],
            "status": r["status"],
            "notes": r["notes"],
            "unit_cost": r["unit_cost"],
            "list_price": r["list_price"],
            "sale_value_at_list": r["list_price"] * r["qty"] if has_price else None,
            "total_cost": r["unit_cost"] * r["qty"] if has_price else None,
            "gross_margin_at_list": (r["list_price"] - r["unit_cost"]) * r["qty"] if has_price else None,
        })

    return {
        "date_today": today,
        "ticket_status_filter": status,
        "note": "Revenue is not modeled in this shop; these are potential sale values, not cash received.",
        "total_sale_value_at_list": sum(t["sale_value_at_list"] or 0 for t in tickets),
        "tickets": tickets,
    }


@mcp.tool
def get_inventory_change_tickets(status: str = "open") -> dict:
    """Track inventory changes and which tickets would alter inventory.

    1. ticket_impacts: for every ticket that requests a SKU + size + qty,
       shows qty on hand, qty requested, qty left after filling it, and any
       shortfall. Tickets with no SKU are listed as not altering inventory.
    2. changes_since_original: compares inventory in the working database
       against the original data/campus_customs.db and lists every SKU/size
       whose qty has changed.
    """
    with get_connection() as conn:
        today = get_date_today(conn)
        rows = conn.execute(
            """
            SELECT t.id AS ticket_id, t.type, t.requester, t.subject, t.sku, t.size, t.qty,
                   inv.name AS item_name, inv.qty AS on_hand, inv.location
            FROM tickets t
            LEFT JOIN inventory inv ON inv.sku = t.sku AND inv.size = t.size
            WHERE t.status = ?
            ORDER BY t.id
            """,
            (status,),
        ).fetchall()
        current = {(r["sku"], r["size"]): dict(r) for r in conn.execute("SELECT * FROM inventory")}

    impacts, no_change = [], []
    for r in rows:
        if r["sku"] is None or r["qty"] is None:
            no_change.append({"ticket_id": r["ticket_id"], "type": r["type"], "subject": r["subject"]})
            continue
        in_inventory = r["on_hand"] is not None
        on_hand = r["on_hand"] if in_inventory else 0
        impacts.append({
            "ticket_id": r["ticket_id"],
            "type": r["type"],
            "requester": r["requester"],
            "subject": r["subject"],
            "sku": r["sku"],
            "item_name": r["item_name"],
            "size": r["size"],
            "location": r["location"],
            "in_inventory_table": in_inventory,
            "qty_on_hand": on_hand,
            "qty_requested": r["qty"],
            "qty_after_if_filled": max(on_hand - r["qty"], 0),
            "can_fill_now": on_hand >= r["qty"],
            "shortfall": max(r["qty"] - on_hand, 0),
        })

    original_conn = sqlite3.connect(f"file:{ORIGINAL_DB_PATH}?mode=ro", uri=True)
    original_conn.row_factory = sqlite3.Row
    with original_conn:
        original = {(r["sku"], r["size"]): dict(r) for r in original_conn.execute("SELECT * FROM inventory")}
    original_conn.close()

    changes = []
    for key in sorted(set(original) | set(current)):
        before = original.get(key, {}).get("qty")
        after = current.get(key, {}).get("qty")
        if before != after:
            changes.append({
                "sku": key[0],
                "size": key[1],
                "name": (current.get(key) or original.get(key))["name"],
                "original_qty": before,
                "current_qty": after,
                "change": (after or 0) - (before or 0),
            })

    return {
        "date_today": today,
        "ticket_status_filter": status,
        "ticket_impacts": impacts,
        "tickets_not_altering_inventory": no_change,
        "changes_since_original": changes,
        "inventory_changed": bool(changes),
    }


# =====================================================================
# Agent-team tools (Problem 5). Every agent gets shop data ONLY through
# these MCP tools. Read tools never change anything; write tools only
# touch the working copy and the board, and pay needs human approval.
# =====================================================================

LOW_STOCK_THRESHOLD = 3
TICKET_STATUSES = {"open", "resolved", "waiting_on_restock", "waiting_on_human", "blocked"}


def add_days(day: str, n: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def add_one_month(day: str) -> str:
    d = date.fromisoformat(day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1])).isoformat()


def open_invoices_for_vendor(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM invoices WHERE vendor_id = ? AND status != 'paid' ORDER BY due_date", (vendor_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def vendor_info(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    open_invoices = open_invoices_for_vendor(conn, row["id"])
    return {
        "id": row["id"],
        "name": row["name"],
        "specialty": row["specialty"],
        "lead_days": row["lead_days"],
        "open_invoice_ids": [i["id"] for i in open_invoices],
        "open_invoice_total": sum(i["amount"] for i in open_invoices),
        "will_ship": not open_invoices,
    }


def require_ticket(conn: sqlite3.Connection, ticket_id: int) -> dict:
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if row is None:
        raise ToolError(f"No ticket with id {ticket_id}.")
    return dict(row)


PREVIEW_KEYS = ("kind", "ref_id", "account", "payee", "description", "amount",
                "cash_before", "cash_after", "can_afford", "problem")


def payment_preview(conn: sqlite3.Connection, kind: str, ref_id: int, account: str) -> dict:
    today = get_date_today(conn)
    p = {"kind": kind, "ref_id": ref_id, "account": account, "payee": None, "description": None,
         "amount": 0.0, "cash_before": 0.0, "cash_after": 0.0, "can_afford": False, "problem": None}
    if kind not in ("invoice", "rent"):
        p["problem"] = "kind must be 'invoice' or 'rent'."
        return p
    acct = conn.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
    if acct is None:
        p["problem"] = f"No cash account named '{account}'."
        return p
    p["cash_before"] = acct["balance"]
    if kind == "invoice":
        inv = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
            (ref_id,),
        ).fetchone()
        if inv is None:
            p["problem"] = f"No invoice with id {ref_id}."
            return p
        p.update(payee=inv["vendor_name"], amount=inv["amount"],
                 description=f"Invoice {ref_id}: {inv['description']} (due {inv['due_date']})")
        if inv["status"] != "open":
            p["problem"] = f"Invoice {ref_id} is already '{inv['status']}'."
    else:
        lease = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
        if lease is None:
            p["problem"] = f"No lease with id {ref_id}."
            return p
        p.update(payee=lease["landlord"], amount=lease["monthly_rent"],
                 description=f"Rent for {lease['space_name']} (due {lease['next_due']})")
        if days_between(today, lease["next_due"]) > 31:
            p["problem"] = f"Rent for lease {ref_id} is already paid through {lease['next_due']}."
    p["cash_after"] = p["cash_before"] - p["amount"]
    p["can_afford"] = p["cash_before"] >= p["amount"]
    return p


# ---------------------------------------------------------------- tickets & board (Boss, Customer service)

@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """One ticket exactly as stored, plus the shop's date_today."""
    with get_connection() as conn:
        return {"date_today": get_date_today(conn), "ticket": require_ticket(conn, ticket_id)}


@mcp.tool
def view_board(ticket_id: int | None = None) -> list[dict]:
    """Drafts and records on the board (all, or just one ticket's). Nothing on the board is ever sent."""
    items = board.load()
    return items if ticket_id is None else [i for i in items if i["ticket_id"] == ticket_id]


# ---------------------------------------------------------------- inventory

@mcp.tool
def check_stock(sku: str, size: str, qty_requested: int | None = None) -> dict:
    """On hand for one SKU/size, the shortfall against qty_requested, and every other size of that SKU."""
    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM inventory WHERE sku = ? ORDER BY rowid", (sku,))]
    match = next((r for r in rows if r["size"] == size), None)
    on_hand = match["qty"] if match else 0
    return {
        "sku": sku,
        "size": size,
        "found": match is not None,
        "name": (match or (rows[0] if rows else {})).get("name"),
        "location": match["location"] if match else None,
        "qty_on_hand": on_hand,
        "qty_requested": qty_requested,
        "shortfall": max((qty_requested or 0) - on_hand, 0),
        "can_fill": None if qty_requested is None else on_hand >= qty_requested,
        "all_sizes": rows,
    }


@mcp.tool
def list_stock_issues() -> dict:
    """Every SKU/size that is out of stock (qty 0) or low (qty <= 3)."""
    with get_connection() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM inventory ORDER BY sku, rowid")]
    return {
        "low_stock_threshold": LOW_STOCK_THRESHOLD,
        "out_of_stock": [r for r in rows if r["qty"] == 0],
        "low_stock": [r for r in rows if 0 < r["qty"] <= LOW_STOCK_THRESHOLD],
    }


@mcp.tool
def list_vendors() -> list[dict]:
    """Vendors with specialty, lead_days, open invoices, and will_ship (False while any invoice is unpaid)."""
    with get_connection() as conn:
        return [vendor_info(conn, r) for r in conn.execute("SELECT * FROM vendors ORDER BY id").fetchall()]


@mcp.tool
def quote_restock(vendor_id: int, sku: str, size: str, qty: int) -> dict:
    """Restock cost (pricing.unit_cost x qty) and arrival (date_today + vendors.lead_days). Flags a blocked vendor."""
    with get_connection() as conn:
        today = get_date_today(conn)
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if vendor is None:
            raise ToolError(f"No vendor with id {vendor_id}.")
        if price is None:
            raise ToolError(f"No pricing row for SKU {sku}.")
        info = vendor_info(conn, vendor)
    blocked = None
    if not info["will_ship"]:
        blocked = (f"{info['name']} will not ship until invoice(s) {info['open_invoice_ids']} "
                   f"(${info['open_invoice_total']:,.2f}) are paid.")
    return {
        "vendor_id": info["id"],
        "vendor_name": info["name"],
        "vendor_specialty": info["specialty"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "unit_cost": price["unit_cost"],
        "total_cost": price["unit_cost"] * qty,
        "lead_days": info["lead_days"],
        "order_date": today,
        "expected_arrival": add_days(today, info["lead_days"]),
        "will_ship": info["will_ship"],
        "blocked_reason": blocked,
    }


@mcp.tool
def draft_vendor_message(ticket_id: int, vendor_id: int, subject: str, body: str) -> dict:
    """Pin a draft message to a vendor on the board. It is NOT sent; a person sends it."""
    with get_connection() as conn:
        require_ticket(conn, ticket_id)
        vendor = conn.execute("SELECT name FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            raise ToolError(f"No vendor with id {vendor_id}.")
        today = get_date_today(conn)
    return board.add("vendor_message", "inventory", f"To {vendor['name']}: {subject}", body, today,
                     ticket_id=ticket_id, data={"vendor_id": vendor_id})


# ---------------------------------------------------------------- accounting

@mcp.tool
def get_cash_position(account: str = "checking") -> dict:
    """Cash balance plus what is owed: open invoices and rent due within 30 days of date_today."""
    with get_connection() as conn:
        today = get_date_today(conn)
        acct = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if acct is None:
            raise ToolError(f"No cash account named '{account}'.")
        invoices_total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS t FROM invoices WHERE status = 'open'"
        ).fetchone()["t"]
        rent_total = sum(r["monthly_rent"] for r in conn.execute("SELECT * FROM leases")
                         if days_between(today, r["next_due"]) <= 30)
    return {
        "account": account,
        "balance": acct["balance"],
        "as_of": today,
        "open_invoices_total": invoices_total,
        "rent_due_next_30_days": rent_total,
        "balance_after_all_obligations": acct["balance"] - invoices_total - rent_total,
    }


@mcp.tool
def list_invoices(status: str = "open") -> list[dict]:
    """Vendor invoices by status ('open' or 'paid') with days_until_due (negative = overdue)."""
    with get_connection() as conn:
        today = get_date_today(conn)
        rows = conn.execute(
            "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
            "WHERE i.status = ? ORDER BY i.due_date", (status,)
        ).fetchall()
    return [{**dict(r), "days_until_due": days_between(today, r["due_date"])} for r in rows]


@mcp.tool
def check_margin(sku: str, qty: int, discount_pct: float = 0) -> dict:
    """Margin on qty of a SKU at list price minus discount_pct (0-100). Flags selling below unit cost."""
    with get_connection() as conn:
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if price is None:
        raise ToolError(f"No pricing row for SKU {sku}.")
    unit_cost, list_price = price["unit_cost"], price["list_price"]
    unit_price = round(list_price * (1 - discount_pct / 100), 2)
    sale_value, total_cost = unit_price * qty, unit_cost * qty
    margin = sale_value - total_cost
    return {
        "sku": sku,
        "qty": qty,
        "unit_cost": unit_cost,
        "list_price": list_price,
        "discount_pct": discount_pct,
        "unit_price_after_discount": unit_price,
        "sale_value": sale_value,
        "total_cost": total_cost,
        "gross_margin": margin,
        "margin_pct": round(100 * margin / sale_value, 1) if sale_value else 0,
        "below_cost": unit_price < unit_cost,
        "max_discount_pct_before_loss": round(100 * (1 - unit_cost / list_price), 1),
    }


@mcp.tool
def preview_payment(kind: str, ref_id: int, account: str = "checking") -> dict:
    """What paying an invoice (kind='invoice', ref_id=invoice id) or rent (kind='rent', ref_id=lease id)
    would do to cash. Moves no money."""
    with get_connection() as conn:
        return payment_preview(conn, kind, ref_id, account)


@mcp.tool
def pay(
    kind: str,
    ref_id: int,
    ticket_id: int,
    account: str = "checking",
    approved_by: str = "",
    payment_request_id: int = 0,
) -> dict:
    """Pay an invoice (kind='invoice', ref_id=invoice id) or rent (kind='rent', ref_id=lease id).

    Requires human approval: leave approved_by and payment_request_id empty, the approval step fills
    them in. Refuses unless that board payment request is approved and matches, and refuses if cash
    is short. When paid, updates cash_accounts, payments, and the invoice or lease.
    """
    request = board.get(payment_request_id) if payment_request_id else None
    if (
        not approved_by.strip()
        or request is None
        or request["kind"] != "payment_request"
        or request["status"] != "approved"
        or request["data"].get("kind") != kind
        or request["data"].get("ref_id") != ref_id
    ):
        raise ToolError("Refused: this payment has no matching human-approved payment request.")

    with get_connection() as conn:
        today = get_date_today(conn)
        p = payment_preview(conn, kind, ref_id, account)
        base = {"kind": kind, "ref_id": ref_id, "amount": p["amount"], "account": account, "ticket_id": ticket_id}
        if p["problem"] or not p["can_afford"]:
            reason = p["problem"] or (f"not enough cash. {account} has ${p['cash_before']:,.2f}, "
                                      f"payment is ${p['amount']:,.2f}.")
            result = {**base, "status": "refused", "cash_after": p["cash_before"], "message": f"Refused: {reason}"}
        else:
            conn.execute("UPDATE cash_accounts SET balance = balance - ?, date = ? WHERE name = ?",
                         (p["amount"], today, account))
            if kind == "invoice":
                conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
            else:
                next_due = conn.execute("SELECT next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()["next_due"]
                conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (add_one_month(next_due), ref_id))
            cur = conn.execute(
                "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
                (kind, ref_id, p["amount"], account, today, approved_by),
            )
            conn.commit()
            result = {**base, "status": "paid", "payment_id": cur.lastrowid, "cash_after": p["cash_after"],
                      "approved_by": approved_by,
                      "message": f"Paid ${p['amount']:,.2f} to {p['payee']} from {account}. "
                                 f"{account} balance is now ${p['cash_after']:,.2f}."}
    board.update(payment_request_id, status=result["status"])
    board.add("payment", "accounting", f"{result['status'].upper()}: {kind} {ref_id} (${p['amount']:,.2f})",
              result["message"], today, ticket_id=ticket_id, status=result["status"], data=result)
    return result


@mcp.tool
def prepare_purchase_order(ticket_id: int, vendor_id: int, sku: str, size: str, qty: int, note: str = "") -> dict:
    """Pin a draft purchase order on the board for a human to check. Never sent or paid.
    Marked blocked if the vendor has an unpaid invoice."""
    with get_connection() as conn:
        require_ticket(conn, ticket_id)
        today = get_date_today(conn)
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        price = conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if vendor is None or price is None:
            raise ToolError("Unknown vendor or SKU.")
        open_invoices = open_invoices_for_vendor(conn, vendor_id)
    total = price["unit_cost"] * qty
    body = (f"{qty} × {sku} size {size} at ${price['unit_cost']:,.2f} = ${total:,.2f}\n"
            f"Vendor lead time: {vendor['lead_days']} days from {today}.")
    if open_invoices:
        body += (f"\n\nBLOCKED: {vendor['name']} will not ship until invoice(s) "
                 f"{[i['id'] for i in open_invoices]} are paid.")
    if note:
        body += f"\n\nNote: {note}"
    return board.add("purchase_order", "accounting", f"PO to {vendor['name']}: {qty} × {sku} {size}", body, today,
                     ticket_id=ticket_id,
                     status="blocked_unpaid_invoice" if open_invoices else "pending_human_check",
                     data={"vendor_id": vendor_id, "sku": sku, "size": size, "qty": qty, "total_cost": total})


# ---------------------------------------------------------------- facilities

@mcp.tool
def list_leases() -> list[dict]:
    """Every lease with monthly rent, next_due, and days_until_due (negative = overdue)."""
    with get_connection() as conn:
        today = get_date_today(conn)
        return [{**dict(r), "days_until_due": days_between(today, r["next_due"])}
                for r in conn.execute("SELECT * FROM leases ORDER BY id")]


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """One lease: space, landlord, monthly rent, next_due, and days_until_due."""
    with get_connection() as conn:
        today = get_date_today(conn)
        row = conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone()
    if row is None:
        raise ToolError(f"No lease with id {lease_id}.")
    return {**dict(row), "days_until_due": days_between(today, row["next_due"])}


@mcp.tool
def draft_facilities_note(ticket_id: int, to: str, subject: str, body: str) -> dict:
    """Pin a draft note (e.g. to the landlord) on the board. It is NOT sent."""
    with get_connection() as conn:
        require_ticket(conn, ticket_id)
        today = get_date_today(conn)
    return board.add("facilities_note", "facilities", f"To {to}: {subject}", body, today, ticket_id=ticket_id)


# ---------------------------------------------------------------- customer service

@mcp.tool
def get_product(sku: str) -> dict:
    """Customer-facing product info: name, list price, and stock by size (no costs)."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM inventory WHERE sku = ? ORDER BY rowid", (sku,)).fetchall()
        price = conn.execute("SELECT list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
    if not rows:
        raise ToolError(f"No product with SKU {sku}.")
    return {"sku": sku, "name": rows[0]["name"], "list_price": price["list_price"] if price else None,
            "sizes_in_stock": {r["size"]: r["qty"] for r in rows}}


@mcp.tool
def draft_customer_message(ticket_id: int, to: str, subject: str, body: str) -> dict:
    """Pin a draft message to a customer on the board. It is NOT emailed; a person sends it."""
    with get_connection() as conn:
        require_ticket(conn, ticket_id)
        today = get_date_today(conn)
    return board.add("customer_message", "customer_service", f"To {to}: {subject}", body, today,
                     ticket_id=ticket_id)


# ---------------------------------------------------------------- run orchestration and the desk API (backend/run.py + backend/main.py only, never given to agents)

@mcp.tool
def list_tickets() -> dict:
    """Every ticket with its status, plus the shop's date_today."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tickets ORDER BY id").fetchall()
        return {"date_today": get_date_today(conn), "tickets": [dict(r) for r in rows]}


@mcp.tool
def approve_purchase_order(purchase_order_id: int, approved_by: str) -> dict:
    """A human approves a draft PO on the board. Refused while the vendor still has an unpaid invoice.
    Approval moves no money; the PO still has to be placed with the vendor by a person."""
    item = board.get(purchase_order_id)
    if item is None or item["kind"] != "purchase_order":
        raise ToolError(f"Board item {purchase_order_id} is not a purchase order.")
    if not approved_by.strip():
        raise ToolError("An approval must name the approver.")
    if item["status"] == "approved":
        raise ToolError(f"Purchase order {purchase_order_id} is already approved.")
    with get_connection() as conn:
        open_invoices = open_invoices_for_vendor(conn, item["data"]["vendor_id"])
    if open_invoices:
        board.update(purchase_order_id, status="blocked_unpaid_invoice")
        raise ToolError(f"Refused: the vendor will not ship until invoice(s) "
                        f"{[i['id'] for i in open_invoices]} are paid.")
    return board.update(purchase_order_id, status="approved", data={"approved_by": approved_by})


@mcp.tool
def start_full_run() -> dict:
    """Reset the working DB from the original and clear the board. Returns date_today and open ticket ids."""
    shutil.copyfile(ORIGINAL_DB_PATH, DB_PATH)
    DB_PATH.chmod(0o644)
    board.clear()
    with get_connection() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM tickets WHERE status = 'open' ORDER BY id")]
        return {"date_today": get_date_today(conn), "open_ticket_ids": ids, "database": DB_PATH.name}


@mcp.tool
def request_payment_approval(ticket_id: int, kind: str, ref_id: int, account: str = "checking") -> dict:
    """Pin a payment request on the board for a human. Returns the board id and the payment preview.

    If this invoice/rent already has an open request on the board, that request is returned
    (already_requested=True) instead of creating a duplicate.
    """
    for item in board.load():
        if (item["kind"] == "payment_request"
                and item["data"].get("kind") == kind and item["data"].get("ref_id") == ref_id
                and item["status"] in ("awaiting_human_approval", "pending_human_approval", "denied", "approved")):
            return {"payment_request_id": item["id"], "already_requested": True, "status": item["status"],
                    "refused_reason": None, "preview": {k: item["data"][k] for k in PREVIEW_KEYS}}
    with get_connection() as conn:
        require_ticket(conn, ticket_id)
        today = get_date_today(conn)
        p = payment_preview(conn, kind, ref_id, account)
    blocked = p["problem"] or (None if p["can_afford"] else
                               f"not enough cash (${p['cash_before']:,.2f} < ${p['amount']:,.2f})")
    body = f"{p['description']}\n\nFrom {account}: ${p['cash_before']:,.2f} → ${p['cash_after']:,.2f}"
    if blocked:
        body += f"\n\nRefused before approval: {blocked}"
    item = board.add("payment_request", "accounting", f"Pay ${p['amount']:,.2f} to {p['payee']}", body, today,
                     ticket_id=ticket_id, status="refused" if blocked else "awaiting_human_approval",
                     data={**p, "ticket_id": ticket_id})
    return {"payment_request_id": item["id"], "already_requested": False, "status": item["status"],
            "refused_reason": blocked, "preview": p}


@mcp.tool
def set_payment_request_status(payment_request_id: int, approved: bool, approver: str = "", note: str = "") -> dict:
    """Record the human's decision on a payment request."""
    item = board.get(payment_request_id)
    if item is None or item["kind"] != "payment_request":
        raise ToolError(f"Board item {payment_request_id} is not a payment request.")
    if approved and not approver.strip():
        raise ToolError("An approval must name the approver.")
    status = "approved" if approved else ("denied" if approver else "pending_human_approval")
    return board.update(payment_request_id, status=status, data={"approver": approver, "note": note})


@mcp.tool
def record_ticket_decision(
    ticket_id: int, status: str, final_call: str, human_follow_ups: list[str], agents_consulted: list[str]
) -> dict:
    """Save the Boss's final call: set tickets.status and pin the decision on the board."""
    if status not in TICKET_STATUSES:
        raise ToolError(f"status must be one of {sorted(TICKET_STATUSES)}.")
    with get_connection() as conn:
        require_ticket(conn, ticket_id)
        today = get_date_today(conn)
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.commit()
    body = final_call + ("\n\nHuman follow-ups:\n" + "\n".join(f"- {f}" for f in human_follow_ups)
                         if human_follow_ups else "")
    return board.add("decision", "boss", f"Final call: {status.replace('_', ' ')}", body, today,
                     ticket_id=ticket_id, status=status,
                     data={"agents_consulted": agents_consulted, "human_follow_ups": human_follow_ups})


if __name__ == "__main__":
    mcp.run()
