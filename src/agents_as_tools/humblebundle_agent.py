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
        # Look for tile data in the HTML
        tile_pattern = r'"tile_name":\s*"([^"]+)".*?"machine_name":\s*"([^"]+)".*?"type":\s*"([^"]+)"'
        matches = re.findall(tile_pattern, html, re.DOTALL)
        
        seen_names = set()
        for match in matches:
            tile_name, machine_name, bundle_type = match
            # Clean up the data
            tile_name = tile_name.strip()
            if tile_name and tile_name not in seen_names:
                seen_names.add(tile_name)
                
                # Determine bundle category based on name and type
                category = "bundle"
                if "book" in tile_name.lower() or "book" in bundle_type.lower():
                    category = "books"
                elif "game" in tile_name.lower() or "game" in bundle_type.lower():
                    category = "games"
                elif "software" in tile_name.lower() or "software" in bundle_type.lower():
                    category = "software"
                
                # Create URL-friendly slug from machine name
                # Extract the base name before _bundle suffix
                slug = machine_name.replace('_', '-')
                if slug.endswith('-bundle'):
                    slug = slug[:-7]
                if slug.endswith('-bookbundle'):
                    slug = slug[:-11]
                if slug.endswith('-gamesbundle'):
                    slug = slug[:-12]
                
                # Construct the URL based on category
                if category == "books":
                    bundle_url = f"https://www.humblebundle.com/books/{slug}"
                elif category == "games":
                    bundle_url = f"https://www.humblebundle.com/games/{slug}"
                elif category == "software":
                    bundle_url = f"https://www.humblebundle.com/software/{slug}"
                else:
                    bundle_url = f"https://www.humblebundle.com/bundles/{slug}"
                
                bundles.append({
                    "name": tile_name,
                    "category": category,
                    "url": bundle_url,
                    "machine_name": machine_name
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
        name_lower = bundle_name.lower()
        matching_url = None
        
        for url in urls:
            if name_lower in url.lower() or any(word in url.lower() for word in name_lower.split()):
                matching_url = url
                break
        
        if not matching_url:
            return f"Bundle '{bundle_name}' not found. Available bundles:\n{bundles_list}"
        
        # Fetch the bundle page
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = httpx.get(matching_url, headers=headers, timeout=30.0, follow_redirects=True)
        response.raise_for_status()
        
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title_tag = soup.find('meta', property='og:title')
        title = title_tag['content'] if title_tag else bundle_name
        
        # Extract description
        desc_tag = soup.find('meta', property='og:description')
        description = desc_tag['content'] if desc_tag else "No description available"
        
        # Try to extract price tiers and content from JSON data
        tier_info = ""
        try:
            # Look for pricing data
            pricing_pattern = r'"tiers":\s*\[(.*?)\]'
            pricing_match = re.search(pricing_pattern, html, re.DOTALL)
            if pricing_match:
                tier_info = "\n\nPrice Tiers: Check the bundle page for current pricing tiers."
        except:
            pass
        
        result = f"Bundle Details:\n\n"
        result += f"Name: {title}\n"
        result += f"Link: {matching_url}\n"
        result += f"Description: {description}\n"
        result += tier_info
        result += f"\n\nVisit the link for full details, pricing, and to purchase."
        
        return result
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching bundle details: {e}")
        return f"Error fetching bundle details: {str(e)}"
    except Exception as e:
        logger.error(f"Error getting bundle details: {e}")
        return f"Error getting bundle details: {str(e)}"
