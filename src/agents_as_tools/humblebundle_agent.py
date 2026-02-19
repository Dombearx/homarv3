"""HumbleBundle agent for checking available bundles."""

import re
from datetime import date
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModelSettings
import httpx
from bs4 import BeautifulSoup
from loguru import logger

HUMBLEBUNDLE_AGENT_PROMPT = """
You are an interface to check Humble Bundle deals and bundles.

You can:
1. List all currently available bundles (games, books, software) from humblebundle.com
2. Get details about specific bundles

When listing bundles, provide:
- Bundle name
- Bundle type (games, books, software)
- Link to the bundle
- Brief description if available

When getting bundle details, provide:
- Full bundle name
- Type
- Direct link
- Description
- Price tiers if visible
- Content included if available

Always provide the direct link so users can visit humblebundle.com to see full details and purchase.

As a response, briefly summarize the available bundles or bundle details.
Do not ask follow up questions.
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
    openai_reasoning_summary="concise",
)

humblebundle_agent = Agent(
    "openai:gpt-5-mini",
    instructions=HUMBLEBUNDLE_AGENT_PROMPT,
    model_settings=settings,
)


@humblebundle_agent.instructions
def add_current_date() -> str:
    """Add current date to agent context."""
    return f"Today is {date.today()}."


def _get_category(product_url: str) -> str:
    """
    Determine bundle category from product URL.

    Args:
        product_url: The product URL path (e.g., "/books/example-bundle")

    Returns:
        Category string: "books", "games", "software", or "bundle"
    """
    if "/books/" in product_url:
        return "books"
    if "/games/" in product_url:
        return "games"
    if "/software/" in product_url:
        return "software"
    return "bundle"


def _find_matching_bundle(bundle_name: str, bundles: list[dict]) -> dict | None:
    """
    Find a matching bundle based on the bundle name.

    Args:
        bundle_name: The name or partial name of the bundle to find
        bundles: List of bundle dictionaries with 'name', 'category', and 'url' keys

    Returns:
        The matching bundle dict or None if not found
    """
    name_lower = bundle_name.lower()

    # First try exact match (case insensitive)
    for bundle in bundles:
        if name_lower == bundle["name"].lower():
            return bundle

    # Then try substring match
    for bundle in bundles:
        if name_lower in bundle["name"].lower():
            return bundle

    # Finally try word-based matching
    search_words = set(name_lower.split())
    for bundle in bundles:
        bundle_words = set(bundle["name"].lower().split())
        # If at least 2 words match (or all search words if less than 2), consider it a match
        matching_words = search_words & bundle_words
        if len(matching_words) >= min(2, len(search_words)):
            return bundle

    return None


def _extract_bundle_metadata(html: str, bundle_name: str) -> dict:
    """
    Extract metadata (title and description) from bundle HTML.

    Args:
        html: The HTML content of the bundle page
        bundle_name: Fallback name if title not found

    Returns:
        Dictionary with 'title' and 'description' keys
    """
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title_tag = soup.find("meta", property="og:title")
    title = title_tag["content"] if title_tag else bundle_name

    # Extract description
    desc_tag = soup.find("meta", property="og:description")
    description = desc_tag["content"] if desc_tag else "No description available"

    return {"title": title, "description": description}


def _extract_price_tiers(html: str) -> list[dict]:
    """
    Extract price tier information from bundle HTML.

    Args:
        html: The HTML content of the bundle page

    Returns:
        List of tier dictionaries with 'price' and 'item_count' keys.
        Returns empty list if no tiers found.
    """
    tiers = []

    try:
        # Look for tier pricing structure in the HTML
        # Pattern 1: Look for price amounts with USD currency
        tier_price_pattern = r'"amount":\s*([\d.]+)\}.*?"currency":\s*"USD"'
        price_matches = re.findall(tier_price_pattern, html, re.DOTALL)

        # Pattern 2: Look for tier item counts
        # Search for tier_item_machine_names arrays
        tier_items_pattern = r'"tier_item_machine_names":\s*\[(.*?)\]'
        tier_items_matches = re.findall(tier_items_pattern, html, re.DOTALL)

        # If we found tier items, count them
        if tier_items_matches:
            for items_str in tier_items_matches:
                items = [x.strip() for x in items_str.split(",") if x.strip()]
                item_count = len(items)
                if item_count > 0:
                    # This represents a tier with items
                    tiers.append(
                        {
                            "price": None,  # Price not associated yet
                            "item_count": item_count,
                        }
                    )

        # Pattern 3: Look for structured tier data with amounts
        structured_tier_pattern = r'"amount_usd":\s*([\d.]+)'
        amount_matches = re.findall(structured_tier_pattern, html)

        # Use structured amounts if found
        if amount_matches:
            unique_amounts = sorted(set(float(x) for x in amount_matches))
            tiers = []
            for amount in unique_amounts:
                tiers.append(
                    {
                        "price": f"${amount:.2f}",
                        "item_count": None,  # Item count not easily associated
                    }
                )

        # Pattern 4: Extract from pay-what-you-want structure
        # Look for suggested prices
        suggested_pattern = (
            r'"price\|money":\s*\{"currency":\s*"USD",\s*"amount":\s*([\d.]+)\}'
        )
        suggested_matches = re.findall(suggested_pattern, html)

        if suggested_matches and not tiers:
            unique_prices = sorted(set(float(x) for x in suggested_matches))
            for price in unique_prices:
                tiers.append({"price": f"${price:.2f}", "item_count": None})

    except Exception as e:
        logger.error(f"Error extracting price tiers: {e}")

    return tiers


def _format_bundle_list(bundles: list[dict]) -> str:
    """
    Format a list of bundles into a human-readable string.

    Args:
        bundles: List of bundle dictionaries with 'name', 'category', and 'url' keys

    Returns:
        Formatted string with bundle information
    """
    result = f"Found {len(bundles)} active bundles:\n\n"
    for bundle in bundles:
        result += f"• {bundle['name']}\n"
        result += f"  Type: {bundle['category']}\n"
        result += f"  Link: {bundle['url']}\n\n"
    return result


def _get_bundles_data(bundle_type: str = "all") -> list[dict]:
    """
    Get raw bundle data from HumbleBundle.com.

    Args:
        bundle_type: Type of bundles to get: "all", "games", "books", or "software"

    Returns:
        List of bundle dictionaries with 'name', 'category', and 'url' keys.
    """
    url = "https://www.humblebundle.com/bundles"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
    response.raise_for_status()

    html = response.text

    bundles = []

    # Extract bundle data from JSON in the page
    # Extract tile names and product URLs separately (they appear in the same order)
    tile_names = [m.group(1) for m in re.finditer(r'"tile_name":\s*"([^"]+)"', html)]
    product_urls = [
        m.group(1) for m in re.finditer(r'"product_url":\s*"([^"]+)"', html)
    ]

    # Pair them up - they should be in the same order
    seen_names = set()
    for tile_name, product_url in zip(tile_names, product_urls):
        # Clean up the data
        tile_name = tile_name.strip()
        if tile_name and tile_name not in seen_names:
            seen_names.add(tile_name)

            # Build full URL
            bundle_url = f"https://www.humblebundle.com{product_url}"

            # Determine category from URL
            category = _get_category(product_url)

            # Filter by bundle type if specified
            if bundle_type != "all" and category != bundle_type:
                continue

            bundles.append({"name": tile_name, "category": category, "url": bundle_url})

    return bundles


@humblebundle_agent.tool_plain
def list_bundles(bundle_type: str = "all") -> str:
    """
    List currently available bundles from HumbleBundle.com.

    Args:
        bundle_type: Type of bundles to list: "all", "games", "books", or "software"

    Returns:
        A formatted string with bundle information including name, type, and link.
    """
    try:
        bundles = _get_bundles_data(bundle_type)

        if not bundles:
            return "No bundles found at this time. Please try again later or visit https://www.humblebundle.com/bundles directly."

        # Format the output
        return _format_bundle_list(bundles)

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching bundles: {e}")
        return f"Error fetching bundle data: {str(e)}. Please try again later."
    except Exception as e:
        logger.error(f"Error listing bundles: {e}")
        return f"Error listing bundles: {str(e)}. Please visit https://www.humblebundle.com/bundles directly."


@humblebundle_agent.tool_plain
def get_bundle_details(bundle_name: str) -> str:
    """
    Get detailed information about a specific bundle.

    Args:
        bundle_name: The name or partial name of the bundle to get details for.

    Returns:
        Detailed information about the bundle including price tiers.
    """
    try:
        # Get the list of bundles to find a match
        bundles = _get_bundles_data()

        # Find matching bundle
        matching_bundle = _find_matching_bundle(bundle_name, bundles)

        if not matching_bundle:
            # Format available bundles for error message
            bundles_list = _format_bundle_list(bundles)
            return (
                f"Bundle '{bundle_name}' not found. Available bundles:\n{bundles_list}"
            )

        # Fetch the bundle page
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = httpx.get(
            matching_bundle["url"], headers=headers, timeout=30.0, follow_redirects=True
        )
        response.raise_for_status()

        html = response.text

        # Extract metadata
        metadata = _extract_bundle_metadata(html, bundle_name)

        # Extract price tiers
        price_tiers = _extract_price_tiers(html)

        # Format result
        result = f"Bundle Details:\n\n"
        result += f"Name: {metadata['title']}\n"
        result += f"Type: {matching_bundle['category']}\n"
        result += f"Link: {matching_bundle['url']}\n"
        result += f"Description: {metadata['description']}\n"

        # Add price tier information if available
        if price_tiers:
            result += f"\n\nPrice Tiers:\n"
            for i, tier in enumerate(price_tiers, 1):
                if tier.get("price"):
                    result += f"  Tier {i}: {tier['price']}"
                    if tier.get("item_count"):
                        result += f" ({tier['item_count']} items)"
                    result += "\n"
        else:
            result += f"\n\nPrice tiers: Visit the link for pricing details"

        result += f"\n\nVisit the link for full details, complete item lists, and to purchase."

        return result

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching bundle details: {e}")
        return f"Error fetching bundle details: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting bundle details: {e}")
        return f"Error getting bundle details: {str(e)}"
