"""Inventory agent: checks stock by SKU/size, spots issues, and picks the restock vendor."""

from pydantic_ai import Agent

from .config import get_model, load_prompt, shop_tools
from .models import InventoryReport, ShopDeps

INVENTORY_TOOLS = {
    "check_stock",
    "list_stock_issues",
    "list_vendors",
    "quote_restock",
    "draft_vendor_message",
    "get_inventory_change_tickets",
}

inventory_agent = Agent(
    get_model(),
    name="inventory",
    deps_type=ShopDeps,
    output_type=InventoryReport,
    instructions=load_prompt("inventory"),
    toolsets=[shop_tools(INVENTORY_TOOLS)],
)
