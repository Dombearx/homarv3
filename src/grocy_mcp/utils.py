from typing import Optional, Any
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Config
GROCY_URL = os.getenv("GROCY_URL")
GROCY_API_KEY = os.getenv("GROCY_API_KEY")
BASE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "GROCY-API-KEY": GROCY_API_KEY,
}


def api_call(
    endpoint: str, method: str = "GET", json: Optional[dict] = None
) -> dict[str, Any]:
    url = f"{GROCY_URL}/api{endpoint}"
    resp = requests.request(method, url, headers=BASE_HEADERS, json=json)
    resp.raise_for_status()
    return resp.json()


def unit_to_name(unit_id: int) -> str:
    """Convert unit ID to name."""
    units = api_call("/objects/quantity_units")
    for unit in units:
        if unit["id"] == unit_id:
            return unit["name"]
    return "Unknown Unit"


def name_to_unit_id(unit_name: str) -> int:
    """Convert unit name to ID."""
    units = api_call("/objects/quantity_units")
    for unit in units:
        if unit["name"].lower() == unit_name.lower():
            return int(unit["id"])
    return -1


def location_to_id(location_name: str) -> int:
    """Convert location name to ID."""
    locations = api_call("/objects/locations")
    for location in locations:
        if location["name"].lower() == location_name.lower():
            return int(location["id"])
    return -1
