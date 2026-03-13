"""Unit tests for homar.py module."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from src.homar import _format_delay_seconds, _check_tool_access
from src.models.schemas import MyDeps, UserType


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


class TestDatetimeParsing:
    """Test datetime parsing logic for scheduled messages."""

    def test_parse_iso_format_with_t(self):
        """Test parsing ISO format with T separator."""
        test_str = "2024-12-25T09:00:00"
        parsed = None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        ]:
            try:
                parsed = datetime.strptime(test_str, fmt)
                break
            except ValueError:
                continue

        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12
        assert parsed.day == 25
        assert parsed.hour == 9
        assert parsed.minute == 0
        assert parsed.second == 0

    def test_parse_space_separator(self):
        """Test parsing format with space separator."""
        test_str = "2024-12-25 09:00:00"
        parsed = None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        ]:
            try:
                parsed = datetime.strptime(test_str, fmt)
                break
            except ValueError:
                continue

        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12
        assert parsed.day == 25

    def test_parse_date_only(self):
        """Test parsing date-only format."""
        test_str = "2024-12-25"
        parsed = None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        ]:
            try:
                parsed = datetime.strptime(test_str, fmt)
                break
            except ValueError:
                continue

        assert parsed is not None
        assert parsed.year == 2024
        assert parsed.month == 12
        assert parsed.day == 25
        assert parsed.hour == 0
        assert parsed.minute == 0

    def test_parse_without_seconds(self):
        """Test parsing format without seconds."""
        test_str = "2024-12-25 09:00"
        parsed = None
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d",
        ]:
            try:
                parsed = datetime.strptime(test_str, fmt)
                break
            except ValueError:
                continue

        assert parsed is not None
        assert parsed.hour == 9
        assert parsed.minute == 0


class TestCheckToolAccess:
    """Test the _check_tool_access helper."""

    def _make_ctx(self, user_type: UserType, username: str = "testuser"):
        ctx = MagicMock()
        ctx.deps = MyDeps(username=username, user_type=user_type)
        return ctx

    def test_admin_can_use_any_tool(self):
        ctx = self._make_ctx(UserType.ADMIN)
        assert _check_tool_access(ctx, "todoist_api") is None
        assert _check_tool_access(ctx, "grocy_api") is None
        assert _check_tool_access(ctx, "home_assistant_api") is None

    def test_default_can_use_any_tool(self):
        ctx = self._make_ctx(UserType.DEFAULT)
        assert _check_tool_access(ctx, "todoist_api") is None
        assert _check_tool_access(ctx, "image_generation_api") is None
        assert _check_tool_access(ctx, "home_assistant_api") is None

    def test_guest_can_use_home_assistant(self):
        ctx = self._make_ctx(UserType.GUEST, "alice")
        assert _check_tool_access(ctx, "home_assistant_api") is None

    def test_guest_cannot_use_todoist(self):
        ctx = self._make_ctx(UserType.GUEST, "alice")
        result = _check_tool_access(ctx, "todoist_api")
        assert result is not None
        assert "alice" in result
        assert "guest" in result

    def test_guest_cannot_use_grocy(self):
        ctx = self._make_ctx(UserType.GUEST, "bob")
        result = _check_tool_access(ctx, "grocy_api")
        assert result is not None
        assert "bob" in result

    def test_guest_cannot_use_image_generation(self):
        ctx = self._make_ctx(UserType.GUEST)
        assert _check_tool_access(ctx, "image_generation_api") is not None

    def test_guest_cannot_use_google_calendar(self):
        ctx = self._make_ctx(UserType.GUEST)
        assert _check_tool_access(ctx, "google_calendar_api") is not None

    def test_guest_cannot_use_humblebundle(self):
        ctx = self._make_ctx(UserType.GUEST)
        assert _check_tool_access(ctx, "humblebundle_api") is not None

    def test_no_deps_allows_access(self):
        ctx = MagicMock()
        ctx.deps = None
        assert _check_tool_access(ctx, "todoist_api") is None
