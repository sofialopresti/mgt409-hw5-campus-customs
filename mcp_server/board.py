"""The shop board, owned by the MCP server: drafts and records, never sent to anyone.

Saved as output/board.json (for tools) and output/board.md (for people).
Cleared at the start of each full run.
"""

import json
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BOARD_JSON = OUTPUT_DIR / "board.json"
BOARD_MD = OUTPUT_DIR / "board.md"


def load() -> list[dict]:
    if not BOARD_JSON.exists():
        return []
    return json.loads(BOARD_JSON.read_text())


def save(items: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BOARD_JSON.write_text(json.dumps(items, indent=2))
    BOARD_MD.write_text(to_markdown(items))


def clear() -> None:
    save([])


def add(
    kind: str,
    author: str,
    title: str,
    body: str,
    created_on: str,
    ticket_id: int | None = None,
    status: str = "draft",
    data: dict[str, Any] | None = None,
) -> dict:
    items = load()
    item = {
        "id": len(items) + 1,
        "kind": kind,
        "author": author,
        "ticket_id": ticket_id,
        "title": title,
        "body": body,
        "status": status,
        "created_on": created_on,
        "data": data or {},
    }
    items.append(item)
    save(items)
    return item


def get(item_id: int) -> dict | None:
    items = load()
    return items[item_id - 1] if 0 < item_id <= len(items) else None


def update(item_id: int, **changes: Any) -> dict:
    items = load()
    item = items[item_id - 1]
    data_changes = changes.pop("data", None)
    item.update(changes)
    if data_changes:
        item["data"].update(data_changes)
    save(items)
    return item


def to_markdown(items: list[dict]) -> str:
    lines = [
        "# Campus Customs Board",
        "",
        "Drafts and records left by the agents. Nothing here has been emailed, called, or sent.",
        "",
    ]
    if not items:
        lines.append("_The board is empty._")
    ticket_ids = sorted({i["ticket_id"] for i in items if i["ticket_id"] is not None})
    groups = [(f"Ticket {t}", [i for i in items if i["ticket_id"] == t]) for t in ticket_ids]
    general = [i for i in items if i["ticket_id"] is None]
    if general:
        groups.append(("General", general))
    for heading, group in groups:
        lines += [f"## {heading}", ""]
        for i in group:
            lines += [
                f"### #{i['id']} · {i['kind'].replace('_', ' ')} · {i['title']}",
                f"_by {i['author']} on {i['created_on']} · status: **{i['status']}**_",
                "",
                i["body"],
                "",
            ]
    return "\n".join(lines)
