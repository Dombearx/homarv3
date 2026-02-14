"""Pytest configuration and shared fixtures."""

import os
import sys
from unittest.mock import MagicMock

# Set fake environment variables to prevent initialization errors
os.environ.setdefault("OPENAI_API_KEY", "fake-key-for-testing")
os.environ.setdefault("RUNPOD_ENDPOINT_ID", "fake-endpoint-for-testing")
os.environ.setdefault("RUNPOD_API_KEY", "fake-key-for-testing")
os.environ.setdefault("DISCORD_TOKEN", "fake-token-for-testing")

# Mock logfire to avoid authentication issues during tests
sys.modules["logfire"] = MagicMock()
