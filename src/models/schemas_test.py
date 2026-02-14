"""Unit tests for models/schemas.py module."""
import pytest
from src.models.schemas import MyDeps, Role, InteractRequest, HealthResponse
from datetime import datetime


class TestRole:
    """Test the Role enum."""

    def test_role_values(self):
        """Test Role enum has expected values."""
        assert Role.USER.value == "user"
        assert Role.ASSISTANT.value == "assistant"

    def test_role_membership(self):
        """Test Role enum membership."""
        assert "user" in [r.value for r in Role]
        assert "assistant" in [r.value for r in Role]


class TestMyDeps:
    """Test the MyDeps dataclass."""

    def test_my_deps_default_values(self):
        """Test MyDeps with default values."""
        deps = MyDeps()
        assert deps.mode == "standard"
        assert deps.thread_id is None
        assert deps.send_message_callback is None

    def test_my_deps_with_values(self):
        """Test MyDeps with custom values."""
        async def callback(msg, thread_id):
            pass
        
        deps = MyDeps(
            mode="horror",
            thread_id=12345,
            send_message_callback=callback
        )
        
        assert deps.mode == "horror"
        assert deps.thread_id == 12345
        assert deps.send_message_callback == callback

    def test_my_deps_partial_values(self):
        """Test MyDeps with partial custom values."""
        deps = MyDeps(mode="test_mode", thread_id=999)
        assert deps.mode == "test_mode"
        assert deps.thread_id == 999
        assert deps.send_message_callback is None


class TestInteractRequest:
    """Test the InteractRequest Pydantic model."""

    def test_interact_request_with_message(self):
        """Test creating InteractRequest with just a message."""
        request = InteractRequest(message="Hello, world!")
        assert request.message == "Hello, world!"
        assert request.user_id is None

    def test_interact_request_with_user_id(self):
        """Test creating InteractRequest with message and user_id."""
        request = InteractRequest(message="Hello", user_id="user123")
        assert request.message == "Hello"
        assert request.user_id == "user123"

    def test_interact_request_validation(self):
        """Test InteractRequest validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            InteractRequest()  # Missing required 'message' field


class TestHealthResponse:
    """Test the HealthResponse Pydantic model."""

    def test_health_response_creation(self):
        """Test creating HealthResponse."""
        now = datetime.now()
        response = HealthResponse(
            status="healthy",
            timestamp=now,
            version="0.1.0"
        )
        
        assert response.status == "healthy"
        assert response.timestamp == now
        assert response.version == "0.1.0"

    def test_health_response_validation(self):
        """Test HealthResponse requires all fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            HealthResponse(status="healthy")  # Missing timestamp and version
