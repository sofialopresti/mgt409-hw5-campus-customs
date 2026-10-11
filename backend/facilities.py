"""Facilities agent: rent, leases, and anything about the shop space."""

from pydantic_ai import Agent

from .config import get_model, load_prompt, shop_tools
from .models import FacilitiesReport, ShopDeps

FACILITIES_TOOLS = {"list_leases", "get_lease", "draft_facilities_note"}

facilities_agent = Agent(
    get_model(),
    name="facilities",
    deps_type=ShopDeps,
    output_type=FacilitiesReport,
    instructions=load_prompt("facilities"),
    toolsets=[shop_tools(FACILITIES_TOOLS)],
)
