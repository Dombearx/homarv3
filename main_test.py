"""Unit tests for main.py utility functions."""
import pytest
from unittest.mock import Mock

from main import _sanitize_thread_name, _get_actual_message, DELAYED_COMMAND_MARKER


class TestSanitizeThreadName:
    """Test the _sanitize_thread_name function."""

    def test_sanitize_normal_string(self):
        """Test sanitizing a normal string."""
        result = _sanitize_thread_name("Hello World")
        assert result == "Hello World"

    def test_sanitize_empty_string(self):
        """Test sanitizing an empty string returns default."""
        result = _sanitize_thread_name("")
        assert result == "discussion"

    def test_sanitize_none(self):
        """Test sanitizing None returns default."""
        result = _sanitize_thread_name(None)
        assert result == "discussion"

    def test_sanitize_whitespace_only(self):
        """Test sanitizing whitespace-only string returns default."""
        result = _sanitize_thread_name("   ")
        assert result == "discussion"

    def test_sanitize_multiple_spaces(self):
        """Test multiple consecutive spaces are collapsed."""
        result = _sanitize_thread_name("Hello    World")
        assert result == "Hello World"

    def test_sanitize_special_characters(self):
        """Test special characters are removed."""
        result = _sanitize_thread_name("Hello@World#Test!")
        assert result == "HelloWorldTest"

    def test_sanitize_allowed_special_chars(self):
        """Test allowed special characters are kept."""
        result = _sanitize_thread_name("Hello-World (test)")
        assert result == "Hello-World (test)"

    def test_sanitize_max_length(self):
        """Test string is truncated to max length."""
        long_string = "a" * 50
        result = _sanitize_thread_name(long_string)
        assert len(result) == 30
        assert result == "a" * 30

    def test_sanitize_max_length_custom(self):
        """Test custom max length."""
        long_string = "abcdefghij"
        result = _sanitize_thread_name(long_string, max_len=5)
        assert len(result) == 5
        assert result == "abcde"


class TestGetActualMessage:
    """Test the _get_actual_message function."""

    def test_get_actual_message_regular(self):
        """Test getting message content from regular message."""
        mock_message = Mock()
        mock_message.content = "Hello, world!"
        
        result = _get_actual_message(mock_message, is_delayed_command=False)
        assert result == "Hello, world!"

    def test_get_actual_message_delayed(self):
        """Test getting message content from delayed command."""
        mock_message = Mock()
        mock_message.content = f"{DELAYED_COMMAND_MARKER} Turn off the lights"
        
        result = _get_actual_message(mock_message, is_delayed_command=True)
        assert result == "Turn off the lights"

    def test_get_actual_message_delayed_with_extra_spaces(self):
        """Test delayed message strips extra spaces."""
        mock_message = Mock()
        mock_message.content = f"{DELAYED_COMMAND_MARKER}   Turn off the lights   "
        
        result = _get_actual_message(mock_message, is_delayed_command=True)
        assert result == "Turn off the lights"

    def test_get_actual_message_delayed_multiword(self):
        """Test delayed message with complex content."""
        mock_message = Mock()
        mock_message.content = f"{DELAYED_COMMAND_MARKER} This is a complex message with many words"
        
        result = _get_actual_message(mock_message, is_delayed_command=True)
        assert result == "This is a complex message with many words"
