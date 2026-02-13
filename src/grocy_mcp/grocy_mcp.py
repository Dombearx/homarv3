from datetime import datetime
from datetime import datetime
from fastmcp import FastMCP

from src.grocy_mcp.models import (
    CreateProductInput,
    AddStockInput,
    ConsumeStockInput,
    OpenStockInput,
    ListStockEntriesInput,
)

from src.grocy_mcp.utils import (
    api_call,
    location_to_id,
    name_to_unit_id,
    unit_to_name,
)

DEFAULT_NOT_FOUND_MESSAGE = "Product not found"


def list_locations() -> str:
    """List all locations."""
    locations = api_call("/objects/locations")
    return "Locations:\n" + "\n".join(
        [f"Name: {location['name']}" for location in locations]
    )


def list_quantity_units() -> str:
    """List all quantity units."""
    quantity_units = api_call("/objects/quantity_units")
    return "Quantity Units:\n" + "\n".join(
        [f"Name: {qu['name']}" for qu in quantity_units]
    )


def list_products() -> str:
    """List all products."""
    products = api_call("/objects/products")
    return "Products:\n" + "\n".join(
        [f"Name: {product['name']}" for product in products]
    )


def get_product(product_name: str) -> int:
    """Get product ID by name"""
    products = api_call(f"/objects/products?search={product_name}")
    for product in products:
        if product["name"].lower() == product_name.lower():
            return int(product["id"])
    return DEFAULT_NOT_FOUND_MESSAGE


mcp = FastMCP("Grocy MCP Server")

@mcp.tool()
def create_product(args: CreateProductInput) -> str:
    """
    Create a new product in Grocy.
    Useful when asked to add stock of a product that does not yet exist.
    """
    try:
        payload = {
            "name": args.product_name,
            "location_id": location_to_id(args.location_name),
            "qu_id_purchase": name_to_unit_id(args.quantity_unit_name),
            "qu_id_stock": name_to_unit_id(args.quantity_unit_name),
            "default_best_before_days_after_open": args.default_best_before_days_after_open,
            "description": f"Created on {datetime.now().strftime('%Y-%m-%d')}",
        }
        api_call("/objects/products", "POST", payload)
        return f"Created: {args.product_name}"
    except Exception as e:
        return f"Error in create_product: {str(e)}"


@mcp.tool()
def list_stocks() -> str:
    """
    List current stock levels.
    Useful when asked about current stock.
    """
    try:
        stocks = api_call("/stock")
        lines = []

        for stock in stocks:
            product = stock.get("product", {})
            bbd = stock.get("best_before_date", "Never expiring")
            unit = product.get("qu_id_stock")
            unit_name = unit_to_name(unit) if unit else "Unknown Unit"

            lines.append(
                f"{product.get('name')}: amount: {stock.get('amount', 0)} {unit_name} "
                f"(Earliest best before date: {bbd}, amount_opened: {stock.get('amount_opened', 0)})"
            )

        return "Stocks:\n" + "\n".join(lines)

    except Exception as e:
        return f"Error in list_stocks: {str(e)}"


@mcp.tool()
def add_stock(args: AddStockInput) -> str:
    """
    Add stock for a product.
    """
    try:
        pid = get_product(args.product_name)
        if pid == DEFAULT_NOT_FOUND_MESSAGE:
            return f'Product "{args.product_name}" not found. Please create it first.'

        payload = {
            "amount": args.amount,
            "best_before_date": args.best_before_date,
        }
        api_call(f"/stock/products/{pid}/add", "POST", payload)
        return f'Added {args.amount} of "{args.product_name}"'

    except Exception as e:
        return f"Error in add_stock: {str(e)}"


@mcp.tool()
def consume_stock(args: ConsumeStockInput) -> str:
    """
    Consume a certain amount of a stock of a product.
    """
    try:
        pid = get_product(args.product_name)
        api_call(f"/stock/products/{pid}/consume", "POST", {"amount": args.amount})
        return f'Consumed {args.amount} of "{args.product_name}".'

    except Exception as e:
        return f"Error in consume_stock: {str(e)}"


@mcp.tool()
def open_stock(args: OpenStockInput) -> str:
    """
    Mark a stock for a product as opened.
    """
    try:
        pid = get_product(args.product_name)
        api_call(f"/stock/products/{pid}/open", "POST", {"amount": args.amount})
        return f'Opened "{args.product_name}".'

    except Exception as e:
        return f"Error in open_stock: {str(e)}"


@mcp.tool()
def list_stock_entries(args: ListStockEntriesInput) -> str:
    """
    List all stock entries for a product. Entries may have different best before dates.
    """
    try:
        pid = get_product(args.product_name)
        entries = api_call(f"/stock/products/{pid}/entries")

        lines = [
            f"Amount: {e['amount']}, BBD: {e.get('best_before_date', 'none')}"
            for e in entries
        ]

        return "Entries:\n" + "\n".join(lines)

    except Exception as e:
        return f"Error in list_stock_entries: {str(e)}"
