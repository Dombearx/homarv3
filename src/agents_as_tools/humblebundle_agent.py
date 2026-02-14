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
    elif "/games/" in product_url:
        return "games"
    elif "/software/" in product_url:
        return "software"
    return "bundle"


def _find_matching_url(bundle_name: str, urls: list[str]) -> str | None:
    """
    Find a matching bundle URL based on the bundle name.
    
    Args:
        bundle_name: The name or partial name of the bundle to find
        urls: List of bundle URLs to search through
        
    Returns:
        The matching URL or None if not found
    """
    name_lower = bundle_name.lower()
    for url in urls:
        if name_lower in url.lower() or any(word in url.lower() for word in name_lower.split()):
            return url
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
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract title
    title_tag = soup.find('meta', property='og:title')
    title = title_tag['content'] if title_tag else bundle_name
    
    # Extract description
    desc_tag = soup.find('meta', property='og:description')
    description = desc_tag['content'] if desc_tag else "No description available"
    
    return {"title": title, "description": description}


def _check_for_pricing_tiers(html: str) -> str:
    """
    Check if bundle has pricing tier information.
    
    Args:
        html: The HTML content of the bundle page
        
    Returns:
        String with pricing tier info or empty string
    """
    try:
        pricing_pattern = r'"tiers":\s*\[(.*?)\]'
        pricing_match = re.search(pricing_pattern, html, re.DOTALL)
        if pricing_match:
            return "\n\nPrice Tiers: Check the bundle page for current pricing tiers."
    except Exception:
        pass
    return ""


@humblebundle_agent.tool_plain
def list_bundles() -> str:
    """
    List all currently available bundles from HumbleBundle.com.
    
    Returns:
        A formatted string with bundle information including name, type, and link.
    """
    try:
        url = "https://www.humblebundle.com/bundles"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        bundles = []
        
        # Extract bundle data from JSON in the page
        # Look for tile data with product URLs in the HTML
        tile_pattern = r'"tile_name":\s*"([^"]+)".*?"product_url":\s*"([^"]+)"'
        matches = re.findall(tile_pattern, html, re.DOTALL)
        
        seen_names = set()
        for match in matches:
            tile_name, product_url = match
            # Clean up the data
            tile_name = tile_name.strip()
            if tile_name and tile_name not in seen_names:
                seen_names.add(tile_name)
                
                # Build full URL
                bundle_url = f"https://www.humblebundle.com{product_url}"
                
                # Determine category from URL
                category = _get_category(product_url)
                
                bundles.append({
                    "name": tile_name,
                    "category": category,
                    "url": bundle_url
                })
        
        if not bundles:
            return "No bundles found at this time. Please try again later or visit https://www.humblebundle.com/bundles directly."
        
        # Format the output
        result = f"Found {len(bundles)} active bundles:\n\n"
        for bundle in bundles:
            result += f"• {bundle['name']}\n"
            result += f"  Type: {bundle['category']}\n"
            result += f"  Link: {bundle['url']}\n\n"
        
        return result
        
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
        Detailed information about the bundle.
    """
    try:
        # First, get the list of bundles to find a match
        bundles_list = list_bundles()
        
        # Extract URLs from the bundles list
        url_pattern = r'Link:\s*(https://www\.humblebundle\.com/[^\s]+)'
        urls = re.findall(url_pattern, bundles_list)
        
        # Find matching bundle
        matching_url = _find_matching_url(bundle_name, urls)
        
        if not matching_url:
            return f"Bundle '{bundle_name}' not found. Available bundles:\n{bundles_list}"
        
        # Fetch the bundle page
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = httpx.get(matching_url, headers=headers, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        
        html = response.text
        
        # Extract metadata
        metadata = _extract_bundle_metadata(html, bundle_name)
        
        # Check for pricing tiers
        tier_info = _check_for_pricing_tiers(html)
        
        # Format result
        result = f"Bundle Details:\n\n"
        result += f"Name: {metadata['title']}\n"
        result += f"Link: {matching_url}\n"
        result += f"Description: {metadata['description']}\n"
        result += tier_info
        result += f"\n\nVisit the link for full details, pricing, and to purchase."
        
        return result
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching bundle details: {e}")
        return f"Error fetching bundle details: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting bundle details: {e}")
        return f"Error getting bundle details: {str(e)}"
