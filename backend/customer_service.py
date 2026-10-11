"""Customer service agent: works with customers and drafts every message to them."""

from pydantic_ai import Agent

from .config import get_model, load_prompt, shop_tools
from .models import CustomerServiceReport, ShopDeps

CUSTOMER_SERVICE_TOOLS = {"get_ticket", "get_product", "draft_customer_message"}

customer_service_agent = Agent(
    get_model(),
    name="customer_service",
    deps_type=ShopDeps,
    output_type=CustomerServiceReport,
    instructions=load_prompt("customer_service"),
    toolsets=[shop_tools(CUSTOMER_SERVICE_TOOLS)],
)
