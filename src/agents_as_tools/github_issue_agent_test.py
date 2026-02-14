"""Unit tests for github_issue_agent.py module."""

from unittest.mock import Mock, patch
from src.agents_as_tools.github_issue_agent import create_github_issue


class TestCreateGitHubIssue:
    """Test the create_github_issue tool function."""

    @patch("src.agents_as_tools.github_issue_agent.Github")
    @patch("src.agents_as_tools.github_issue_agent.Auth")
    @patch.dict(
        "os.environ", {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "test/repo"}
    )
    def test_create_issue_success(self, mock_auth, mock_github):
        """Test successful issue creation."""
        # Setup mocks
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.html_url = "https://github.com/test/repo/issues/123"

        mock_repo = Mock()
        mock_repo.create_issue.return_value = mock_issue

        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance

        # Call function
        result = create_github_issue(
            title="Test Issue", body="Test body", labels=["bug", "enhancement"]
        )

        # Assertions
        assert "Successfully created issue #123" in result
        assert "https://github.com/test/repo/issues/123" in result
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue", body="Test body", labels=["bug", "enhancement"]
        )

    @patch("src.agents_as_tools.github_issue_agent.Github")
    @patch("src.agents_as_tools.github_issue_agent.Auth")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_create_issue_without_labels(self, mock_auth, mock_github):
        """Test issue creation without labels."""
        # Setup mocks
        mock_issue = Mock()
        mock_issue.number = 456
        mock_issue.html_url = "https://github.com/Dombearx/homarv3/issues/456"

        mock_repo = Mock()
        mock_repo.create_issue.return_value = mock_issue

        mock_github_instance = Mock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance

        # Call function without labels
        result = create_github_issue(
            title="Test Issue Without Labels", body="Test body"
        )

        # Assertions
        assert "Successfully created issue #456" in result
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue Without Labels", body="Test body", labels=[]
        )

    @patch.dict("os.environ", {}, clear=True)
    def test_create_issue_missing_token(self):
        """Test error handling when GITHUB_TOKEN is not set."""
        result = create_github_issue(title="Test Issue", body="Test body")

        assert "Error: GITHUB_TOKEN environment variable is not set" in result

    @patch("src.agents_as_tools.github_issue_agent.Github")
    @patch("src.agents_as_tools.github_issue_agent.Auth")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_create_issue_github_exception(self, mock_auth, mock_github):
        """Test handling of GitHub API exceptions."""
        from github import GithubException

        # Setup mocks to raise exception
        mock_github_instance = Mock()
        mock_repo = Mock()

        # Create a mock exception with proper structure
        error_data = {"message": "Repository not found"}
        mock_exception = GithubException(404, error_data)
        mock_repo.create_issue.side_effect = mock_exception

        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance

        # Call function
        result = create_github_issue(title="Test Issue", body="Test body")

        # Assertions
        assert "GitHub API error:" in result
        assert "404" in result

    @patch("src.agents_as_tools.github_issue_agent.Github")
    @patch("src.agents_as_tools.github_issue_agent.Auth")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"})
    def test_create_issue_generic_exception(self, mock_auth, mock_github):
        """Test handling of generic exceptions."""
        # Setup mocks to raise exception
        mock_github.side_effect = Exception("Connection failed")

        # Call function
        result = create_github_issue(title="Test Issue", body="Test body")

        # Assertions
        assert "Error creating issue:" in result
        assert "Connection failed" in result
