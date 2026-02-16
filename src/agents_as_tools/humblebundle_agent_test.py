"""Unit tests for humblebundle_agent.py module."""

import pytest
from unittest.mock import Mock, patch
from src.agents_as_tools.humblebundle_agent import (
    list_bundles,
    get_bundle_details,
    _get_category,
    _find_matching_url,
    _extract_bundle_metadata,
    _format_bundle_list,
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
    @patch("src.agents_as_tools.humblebundle_agent.list_bundles")
    def test_get_bundle_details_success(self, mock_list, mock_get):
        """Test successful bundle detail retrieval."""
        # Mock list_bundles to return a bundle
        mock_list.return_value = """
        Found 1 active bundles:
        
        • Test Bundle
          Type: games
          Link: https://www.humblebundle.com/games/test-bundle
        """

        # Mock detail page response
        mock_html = """
        <html>
        <head>
        <meta property="og:title" content="Test Bundle">
        <meta property="og:description" content="A great test bundle">
        </head>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = get_bundle_details("test")

        assert "Test Bundle" in result
        assert "https://www.humblebundle.com" in result

    @patch("src.agents_as_tools.humblebundle_agent.list_bundles")
    def test_get_bundle_details_not_found(self, mock_list):
        """Test when bundle is not found."""
        mock_list.return_value = "Found 0 bundles"

        result = get_bundle_details("nonexistent")

        assert "not found" in result.lower()

    @patch("src.agents_as_tools.humblebundle_agent.httpx.get")
    @patch("src.agents_as_tools.humblebundle_agent.list_bundles")
    def test_get_bundle_details_http_error(self, mock_list, mock_get):
        """Test handling of HTTP errors when fetching details."""
        import httpx

        mock_list.return_value = """
        Link: https://www.humblebundle.com/games/test
        """
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


class TestFindMatchingUrl:
    """Test the _find_matching_url helper function."""

    def test_find_matching_url_exact_match(self):
        """Test finding URL with exact name match."""
        urls = [
            "https://www.humblebundle.com/games/test-bundle",
            "https://www.humblebundle.com/books/other-bundle",
        ]
        result = _find_matching_url("test", urls)
        assert result == "https://www.humblebundle.com/games/test-bundle"

    def test_find_matching_url_partial_match(self):
        """Test finding URL with partial name match."""
        urls = [
            "https://www.humblebundle.com/games/awesome-rpg-bundle",
            "https://www.humblebundle.com/books/python-books",
        ]
        result = _find_matching_url("rpg", urls)
        assert result == "https://www.humblebundle.com/games/awesome-rpg-bundle"

    def test_find_matching_url_word_match(self):
        """Test finding URL with word-based matching."""
        urls = [
            "https://www.humblebundle.com/games/fallout-tabletop",
            "https://www.humblebundle.com/books/programming",
        ]
        result = _find_matching_url("fallout", urls)
        assert result == "https://www.humblebundle.com/games/fallout-tabletop"

    def test_find_matching_url_not_found(self):
        """Test when no matching URL is found."""
        urls = [
            "https://www.humblebundle.com/games/test-bundle",
        ]
        result = _find_matching_url("nonexistent", urls)
        assert result is None

    def test_find_matching_url_empty_list(self):
        """Test with empty URL list."""
        result = _find_matching_url("test", [])
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
