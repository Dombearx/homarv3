"""Unit tests for humblebundle_agent.py module."""

import pytest
from unittest.mock import Mock, patch
from src.agents_as_tools.humblebundle_agent import list_bundles, get_bundle_details


class TestListBundles:
    """Test the list_bundles function."""

    @patch('src.agents_as_tools.humblebundle_agent.httpx.get')
    def test_list_bundles_success(self, mock_get):
        """Test successful bundle listing."""
        # Mock HTML response with bundle data
        mock_html = '''
        <html>
        <body>
        <script>
        var data = {
            "tile_name": "Humble Game Bundle: Test Games",
            "machine_name": "testgames_gamesbundle",
            "type": "games"
        };
        var data2 = {
            "tile_name": "Humble Book Bundle: Test Books",
            "machine_name": "testbooks_bookbundle",
            "type": "books"
        };
        </script>
        </body>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = list_bundles()
        
        assert "Humble Game Bundle: Test Games" in result
        assert "Humble Book Bundle: Test Books" in result
        assert "https://www.humblebundle.com" in result
        assert "games" in result and "books" in result

    @patch('src.agents_as_tools.humblebundle_agent.httpx.get')
    def test_list_bundles_no_bundles(self, mock_get):
        """Test when no bundles are found."""
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = list_bundles()
        
        assert "No bundles found" in result or "try again" in result.lower()

    @patch('src.agents_as_tools.humblebundle_agent.httpx.get')
    def test_list_bundles_http_error(self, mock_get):
        """Test handling of HTTP errors."""
        import httpx
        mock_get.side_effect = httpx.HTTPError("Connection failed")
        
        result = list_bundles()
        
        assert "Error" in result

    @patch('src.agents_as_tools.humblebundle_agent.httpx.get')
    def test_list_bundles_generic_exception(self, mock_get):
        """Test handling of generic exceptions."""
        mock_get.side_effect = Exception("Unexpected error")
        
        result = list_bundles()
        
        assert "Error" in result


class TestGetBundleDetails:
    """Test the get_bundle_details function."""

    @patch('src.agents_as_tools.humblebundle_agent.httpx.get')
    @patch('src.agents_as_tools.humblebundle_agent.list_bundles')
    def test_get_bundle_details_success(self, mock_list, mock_get):
        """Test successful bundle detail retrieval."""
        # Mock list_bundles to return a bundle
        mock_list.return_value = '''
        Found 1 active bundles:
        
        • Test Bundle
          Type: games
          Link: https://www.humblebundle.com/games/test-bundle
        '''
        
        # Mock detail page response
        mock_html = '''
        <html>
        <head>
        <meta property="og:title" content="Test Bundle">
        <meta property="og:description" content="A great test bundle">
        </head>
        </html>
        '''
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = get_bundle_details("test")
        
        assert "Test Bundle" in result
        assert "https://www.humblebundle.com" in result

    @patch('src.agents_as_tools.humblebundle_agent.list_bundles')
    def test_get_bundle_details_not_found(self, mock_list):
        """Test when bundle is not found."""
        mock_list.return_value = "Found 0 bundles"
        
        result = get_bundle_details("nonexistent")
        
        assert "not found" in result.lower()

    @patch('src.agents_as_tools.humblebundle_agent.httpx.get')
    @patch('src.agents_as_tools.humblebundle_agent.list_bundles')
    def test_get_bundle_details_http_error(self, mock_list, mock_get):
        """Test handling of HTTP errors when fetching details."""
        import httpx
        mock_list.return_value = '''
        Link: https://www.humblebundle.com/games/test
        '''
        mock_get.side_effect = httpx.HTTPError("Connection failed")
        
        result = get_bundle_details("test")
        
        assert "Error" in result
