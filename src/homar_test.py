"""Unit tests for homar.py module."""

import pytest
from datetime import datetime, timedelta
from src.homar import _format_delay_seconds


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
