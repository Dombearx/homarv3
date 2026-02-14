"""Unit tests for homar.py module."""

import pytest
from src.homar import _format_delay_seconds
from src.models.schemas import MyDeps


class TestFormatDelaySeconds:
    """Test the _format_delay_seconds utility function."""

    def test_format_seconds_under_minute(self):
        """Test formatting delays less than a minute."""
        assert _format_delay_seconds(1) == "1 seconds"
        assert _format_delay_seconds(30) == "30 seconds"
        assert _format_delay_seconds(59) == "59 seconds"

    def test_format_minutes(self):
        """Test formatting delays in minutes."""
        assert _format_delay_seconds(60) == "1 minutes"
        assert _format_delay_seconds(120) == "2 minutes"
        assert _format_delay_seconds(1800) == "30 minutes"
        assert _format_delay_seconds(3599) == "59 minutes"

    def test_format_hours_only(self):
        """Test formatting delays that are exact hours."""
        assert _format_delay_seconds(3600) == "1 hours"
        assert _format_delay_seconds(7200) == "2 hours"
        assert _format_delay_seconds(86400) == "24 hours"

    def test_format_hours_and_minutes(self):
        """Test formatting delays with both hours and minutes."""
        assert _format_delay_seconds(3660) == "1 hours and 1 minutes"
        assert (
            _format_delay_seconds(7200) == "2 hours"
        )  # Exact 2 hours, no minutes shown
        assert _format_delay_seconds(5400) == "1 hours and 30 minutes"
        assert _format_delay_seconds(9000) == "2 hours and 30 minutes"


class TestMyDeps:
    """Test MyDeps dataclass for image tracking."""

    def test_mydeps_default_initialization(self):
        """Test MyDeps initializes with empty image list by default."""
        deps = MyDeps()
        assert deps.generated_images == []
        assert deps.mode == "standard"
        assert deps.thread_id is None
        assert deps.send_message_callback is None

    def test_mydeps_with_custom_values(self):
        """Test MyDeps can be initialized with custom values."""
        deps = MyDeps(
            mode="horror",
            thread_id=12345,
            send_message_callback=lambda x: x,
            generated_images=["/path/to/image.png"],
        )
        assert deps.mode == "horror"
        assert deps.thread_id == 12345
        assert deps.send_message_callback is not None
        assert deps.generated_images == ["/path/to/image.png"]

    def test_mydeps_can_append_images(self):
        """Test that images can be appended to generated_images list."""
        deps = MyDeps()
        deps.generated_images.append("/path/to/image1.png")
        deps.generated_images.append("/path/to/image2.png")
        assert len(deps.generated_images) == 2
        assert "/path/to/image1.png" in deps.generated_images
        assert "/path/to/image2.png" in deps.generated_images
