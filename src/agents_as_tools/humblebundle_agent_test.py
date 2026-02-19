"""Unit tests for humblebundle_agent.py module."""

import pytest
from unittest.mock import Mock, patch
from src.agents_as_tools.humblebundle_agent import (
    list_bundles,
    get_bundle_details,
    _get_category,
    _find_matching_bundle,
    _extract_bundle_metadata,
    _extract_price_tiers,
    _format_bundle_list,
    _get_bundles_data,
)


class TestListBundles:
    """Test the list_bundles function."""

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    def test_list_bundles_success(self, mock_get):
        """Test successful bundle listing."""
        # Mock HTML response with bundle data
        mock_html = """
        <html>
        <body>
        <script>
        var data = {
            "tile_name": "Humble Game Bundle: Test Games",
            "product_url": "/games/test-games"
        };
        var data2 = {
            "tile_name": "Humble Book Bundle: Test Books",
            "product_url": "/books/test-books"
        };
        </script>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = list_bundles()

        assert "Humble Game Bundle: Test Games" in result
        assert "Humble Book Bundle: Test Books" in result
        assert "https://www.humblebundle.com" in result
        assert "games" in result and "books" in result

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    def test_list_bundles_no_bundles(self, mock_get):
        """Test when no bundles are found."""
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = list_bundles()

        assert "No bundles found" in result or "try again" in result.lower()

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    def test_list_bundles_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        import httpx

        mock_get.side_effect = httpx.HTTPError("Connection failed")

        result = list_bundles()

        assert "Error" in result

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    def test_list_bundles_generic_exception(self, mock_get):
        """Test handling of generic exceptions."""
        mock_get.side_effect = Exception("Unexpected error")

        result = list_bundles()

        assert "Error" in result

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    def test_list_bundles_filter_by_games(self, mock_get):
        """Test filtering bundles by games type."""
        mock_html = """
        <html>
        <body>
        <script>
        var data = {
            "tile_name": "Humble Game Bundle: Test Games",
            "product_url": "/games/test-games"
        };
        var data2 = {
            "tile_name": "Humble Book Bundle: Test Books",
            "product_url": "/books/test-books"
        };
        </script>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = list_bundles(bundle_type="games")

        assert "Humble Game Bundle: Test Games" in result
        assert "Humble Book Bundle: Test Books" not in result

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    def test_list_bundles_filter_by_books(self, mock_get):
        """Test filtering bundles by books type."""
        mock_html = """
        <html>
        <body>
        <script>
        var data = {
            "tile_name": "Humble Game Bundle: Test Games",
            "product_url": "/games/test-games"
        };
        var data2 = {
            "tile_name": "Humble Book Bundle: Test Books",
            "product_url": "/books/test-books"
        };
        </script>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = list_bundles(bundle_type="books")

        assert "Humble Book Bundle: Test Books" in result
        assert "Humble Game Bundle: Test Games" not in result


class TestGetBundleDetails:
    """Test the get_bundle_details function."""

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    @patch("src.agents_as_tools.humblebundle_agent._get_bundles_data")
    def test_get_bundle_details_success(self, mock_get_bundles, mock_get):
        """Test successful bundle detail retrieval."""
        # Mock _get_bundles_data to return a bundle
        mock_get_bundles.return_value = [
            {
                "name": "Test Bundle",
                "category": "games",
                "url": "https://www.humblebundle.com/games/test-bundle",
            }
        ]

        # Mock detail page response
        mock_html = """
        <html>
        <head>
        <meta property="og:title" content="Test Bundle">
        <meta property="og:description" content="A great test bundle">
        </head>
        <body>
        <script>
        var data = {"amount": 15.00}, "currency": "USD"};
        var data2 = {"amount": 25.00}, "currency": "USD"};
        </script>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_bundle_details("test")

        assert "Test Bundle" in result
        assert "https://www.humblebundle.com" in result
        assert "games" in result

    @patch("src.agents_as_tools.humblebundle_agent._get_bundles_data")
    def test_get_bundle_details_not_found(self, mock_get_bundles):
        """Test when bundle is not found."""
        mock_get_bundles.return_value = []

        result = get_bundle_details("nonexistent")

        assert "not found" in result.lower()

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    @patch("src.agents_as_tools.humblebundle_agent._get_bundles_data")
    def test_get_bundle_details_http_error(self, mock_get_bundles, mock_get):
        """Test handling of HTTP errors when fetching details."""
        import httpx

        mock_get_bundles.return_value = [
            {
                "name": "Test Bundle",
                "category": "games",
                "url": "https://www.humblebundle.com/games/test",
            }
        ]
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        result = get_bundle_details("test")

        assert "Error" in result


class TestGetCategory:
    """Test the _get_category helper function."""

    def test_get_category_books(self):
        """Test category detection for books."""
        assert _get_category("/books/example-bundle") == "books"

    def test_get_category_games(self):
        """Test category detection for games."""
        assert _get_category("/games/example-bundle") == "games"

    def test_get_category_software(self):
        """Test category detection for software."""
        assert _get_category("/software/example-bundle") == "software"

    def test_get_category_default(self):
        """Test default category for other bundle types."""
        assert _get_category("/bundles/example-bundle") == "bundle"
        assert _get_category("/other/example") == "bundle"


class TestFindMatchingBundle:
    """Test the _find_matching_bundle helper function."""

    def test_find_matching_bundle_exact_match(self):
        """Test finding bundle with exact name match."""
        bundles = [
            {
                "name": "Test Bundle",
                "category": "games",
                "url": "https://www.humblebundle.com/games/test-bundle",
            },
            {
                "name": "Other Bundle",
                "category": "books",
                "url": "https://www.humblebundle.com/books/other-bundle",
            },
        ]
        result = _find_matching_bundle("Test Bundle", bundles)
        assert result is not None
        assert result["name"] == "Test Bundle"

    def test_find_matching_bundle_case_insensitive(self):
        """Test finding bundle with case-insensitive match."""
        bundles = [
            {
                "name": "Test Bundle",
                "category": "games",
                "url": "https://www.humblebundle.com/games/test-bundle",
            }
        ]
        result = _find_matching_bundle("test bundle", bundles)
        assert result is not None
        assert result["name"] == "Test Bundle"

    def test_find_matching_bundle_partial_match(self):
        """Test finding bundle with partial name match."""
        bundles = [
            {
                "name": "Humble RPG Bundle: Awesome Games",
                "category": "games",
                "url": "https://www.humblebundle.com/games/awesome-rpg-bundle",
            },
            {
                "name": "Humble Book Bundle: Programming",
                "category": "books",
                "url": "https://www.humblebundle.com/books/programming",
            },
        ]
        result = _find_matching_bundle("RPG", bundles)
        assert result is not None
        assert "RPG" in result["name"]

    def test_find_matching_bundle_word_match(self):
        """Test finding bundle with word-based matching."""
        bundles = [
            {
                "name": "Humble Game Bundle: Fallout Tabletop",
                "category": "games",
                "url": "https://www.humblebundle.com/games/fallout-tabletop",
            },
            {
                "name": "Humble Book Bundle: Programming",
                "category": "books",
                "url": "https://www.humblebundle.com/books/programming",
            },
        ]
        result = _find_matching_bundle("Fallout Tabletop", bundles)
        assert result is not None
        assert "Fallout" in result["name"]

    def test_find_matching_bundle_not_found(self):
        """Test when no matching bundle is found."""
        bundles = [
            {
                "name": "Test Bundle",
                "category": "games",
                "url": "https://www.humblebundle.com/games/test-bundle",
            }
        ]
        result = _find_matching_bundle("nonexistent", bundles)
        assert result is None

    def test_find_matching_bundle_empty_list(self):
        """Test with empty bundle list."""
        result = _find_matching_bundle("test", [])
        assert result is None


class TestExtractBundleMetadata:
    """Test the _extract_bundle_metadata helper function."""

    def test_extract_metadata_with_all_tags(self):
        """Test extracting metadata when all tags are present."""
        html = """
        <html>
        <head>
        <meta property="og:title" content="Test Bundle Title">
        <meta property="og:description" content="Test bundle description">
        </head>
        </html>
        """
        result = _extract_bundle_metadata(html, "Fallback Name")
        assert result["title"] == "Test Bundle Title"
        assert result["description"] == "Test bundle description"

    def test_extract_metadata_missing_title(self):
        """Test extracting metadata when title tag is missing."""
        html = """
        <html>
        <head>
        <meta property="og:description" content="Test description">
        </head>
        </html>
        """
        result = _extract_bundle_metadata(html, "Fallback Name")
        assert result["title"] == "Fallback Name"
        assert result["description"] == "Test description"

    def test_extract_metadata_missing_description(self):
        """Test extracting metadata when description tag is missing."""
        html = """
        <html>
        <head>
        <meta property="og:title" content="Test Title">
        </head>
        </html>
        """
        result = _extract_bundle_metadata(html, "Fallback Name")
        assert result["title"] == "Test Title"
        assert result["description"] == "No description available"

    def test_extract_metadata_all_missing(self):
        """Test extracting metadata when all tags are missing."""
        html = "<html><head></head></html>"
        result = _extract_bundle_metadata(html, "Fallback Name")
        assert result["title"] == "Fallback Name"
        assert result["description"] == "No description available"


class TestExtractPriceTiers:
    """Test the _extract_price_tiers helper function."""

    def test_extract_price_tiers_with_amounts(self):
        """Test extracting price tiers with amount_usd."""
        html = """
        <html>
        <body>
        <script>
        var data = {"amount_usd": 15.00};
        var data2 = {"amount_usd": 25.00};
        var data3 = {"amount_usd": 35.00};
        </script>
        </body>
        </html>
        """
        result = _extract_price_tiers(html)
        assert len(result) > 0
        # Check that at least one tier was extracted
        assert any("$" in tier.get("price", "") for tier in result)

    def test_extract_price_tiers_with_pay_what_you_want(self):
        """Test extracting price tiers from pay-what-you-want structure."""
        html = """
        <html>
        <body>
        <script>
        var data = {"price|money": {"currency": "USD", "amount": 16.00}};
        var data2 = {"price|money": {"currency": "USD", "amount": 25.00}};
        </script>
        </body>
        </html>
        """
        result = _extract_price_tiers(html)
        assert len(result) > 0

    def test_extract_price_tiers_no_data(self):
        """Test extracting price tiers when no data available."""
        html = "<html><body></body></html>"
        result = _extract_price_tiers(html)
        assert isinstance(result, list)
        # May be empty or have minimal data


class TestFormatBundleList:
    """Test the _format_bundle_list helper function."""

    def test_format_bundle_list_single(self):
        """Test formatting a single bundle."""
        bundles = [
            {
                "name": "Test Bundle",
                "category": "games",
                "url": "https://www.humblebundle.com/games/test",
            }
        ]
        result = _format_bundle_list(bundles)
        assert "Found 1 active bundles" in result
        assert "Test Bundle" in result
        assert "games" in result
        assert "https://www.humblebundle.com/games/test" in result

    def test_format_bundle_list_multiple(self):
        """Test formatting multiple bundles."""
        bundles = [
            {
                "name": "Game Bundle",
                "category": "games",
                "url": "https://www.humblebundle.com/games/test1",
            },
            {
                "name": "Book Bundle",
                "category": "books",
                "url": "https://www.humblebundle.com/books/test2",
            },
        ]
        result = _format_bundle_list(bundles)
        assert "Found 2 active bundles" in result
        assert "Game Bundle" in result
        assert "Book Bundle" in result
        assert "games" in result
        assert "books" in result

    def test_format_bundle_list_empty(self):
        """Test formatting empty bundle list."""
        bundles = []
        result = _format_bundle_list(bundles)
        assert "Found 0 active bundles" in result
