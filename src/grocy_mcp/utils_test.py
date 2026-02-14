"""Unit tests for grocy_mcp/utils.py module.

Note: These tests focus on the utility functions' logic, not the actual API calls.
We test the search/matching logic without making real HTTP requests.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.grocy_mcp.utils import unit_to_name, name_to_unit_id, location_to_id


class TestUnitToName:
    """Test the unit_to_name function."""

    @patch("src.grocy_mcp.utils.api_call")
    def test_unit_to_name_found(self, mock_api_call):
        """Test converting unit ID to name when unit exists."""
        mock_api_call.return_value = [
            {"id": 1, "name": "piece"},
            {"id": 2, "name": "kg"},
            {"id": 3, "name": "liter"},
        ]

        result = unit_to_name(2)
        assert result == "kg"

    @patch("src.grocy_mcp.utils.api_call")
    def test_unit_to_name_not_found(self, mock_api_call):
        """Test converting unit ID to name when unit doesn't exist."""
        mock_api_call.return_value = [
            {"id": 1, "name": "piece"},
            {"id": 2, "name": "kg"},
        ]

        result = unit_to_name(999)
        assert result == "Unknown Unit"

    @patch("src.grocy_mcp.utils.api_call")
    def test_unit_to_name_empty_list(self, mock_api_call):
        """Test converting unit ID when no units exist."""
        mock_api_call.return_value = []

        result = unit_to_name(1)
        assert result == "Unknown Unit"


class TestNameToUnitId:
    """Test the name_to_unit_id function."""

    @patch("src.grocy_mcp.utils.api_call")
    def test_name_to_unit_id_found(self, mock_api_call):
        """Test converting unit name to ID when unit exists."""
        mock_api_call.return_value = [
            {"id": 1, "name": "piece"},
            {"id": 2, "name": "kg"},
            {"id": 3, "name": "liter"},
        ]

        result = name_to_unit_id("kg")
        assert result == 2

    @patch("src.grocy_mcp.utils.api_call")
    def test_name_to_unit_id_case_insensitive(self, mock_api_call):
        """Test unit name matching is case-insensitive."""
        mock_api_call.return_value = [
            {"id": 1, "name": "piece"},
            {"id": 2, "name": "KG"},
            {"id": 3, "name": "liter"},
        ]

        result = name_to_unit_id("kg")
        assert result == 2

    @patch("src.grocy_mcp.utils.api_call")
    def test_name_to_unit_id_not_found(self, mock_api_call):
        """Test converting unit name to ID when unit doesn't exist."""
        mock_api_call.return_value = [
            {"id": 1, "name": "piece"},
            {"id": 2, "name": "kg"},
        ]

        result = name_to_unit_id("nonexistent")
        assert result == -1

    @patch("src.grocy_mcp.utils.api_call")
    def test_name_to_unit_id_empty_list(self, mock_api_call):
        """Test converting unit name when no units exist."""
        mock_api_call.return_value = []

        result = name_to_unit_id("kg")
        assert result == -1


class TestLocationToId:
    """Test the location_to_id function."""

    @patch("src.grocy_mcp.utils.api_call")
    def test_location_to_id_found(self, mock_api_call):
        """Test converting location name to ID when location exists."""
        mock_api_call.return_value = [
            {"id": 1, "name": "Fridge"},
            {"id": 2, "name": "Pantry"},
            {"id": 3, "name": "Freezer"},
        ]

        result = location_to_id("Pantry")
        assert result == 2

    @patch("src.grocy_mcp.utils.api_call")
    def test_location_to_id_case_insensitive(self, mock_api_call):
        """Test location name matching is case-insensitive."""
        mock_api_call.return_value = [
            {"id": 1, "name": "FRIDGE"},
            {"id": 2, "name": "Pantry"},
        ]

        result = location_to_id("fridge")
        assert result == 1

    @patch("src.grocy_mcp.utils.api_call")
    def test_location_to_id_not_found(self, mock_api_call):
        """Test converting location name to ID when location doesn't exist."""
        mock_api_call.return_value = [
            {"id": 1, "name": "Fridge"},
            {"id": 2, "name": "Pantry"},
        ]

        result = location_to_id("Garage")
        assert result == -1

    @patch("src.grocy_mcp.utils.api_call")
    def test_location_to_id_empty_list(self, mock_api_call):
        """Test converting location name when no locations exist."""
        mock_api_call.return_value = []

        result = location_to_id("Fridge")
        assert result == -1
