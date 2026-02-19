"""Unit tests for src/models/schemas.py."""

from src.models.schemas import (
    UserType,
    USER_REGISTRY,
    GUEST_ALLOWED_TOOLS,
    get_user_type,
    MyDeps,
)


class TestUserType:
    """Test the UserType enum values."""

    def test_enum_values_exist(self):
        assert UserType.ADMIN == "admin"
        assert UserType.DEFAULT == "default"
        assert UserType.GUEST == "guest"


class TestGuestAllowedTools:
    """Test that GUEST_ALLOWED_TOOLS contains only home_assistant_api."""

    def test_home_assistant_allowed(self):
        assert "home_assistant_api" in GUEST_ALLOWED_TOOLS

    def test_other_tools_not_allowed(self):
        for tool in (
            "todoist_api",
            "grocy_api",
            "image_generation_api",
            "google_calendar_api",
            "humblebundle_api",
        ):
            assert tool not in GUEST_ALLOWED_TOOLS


class TestGetUserType:
    """Test the get_user_type helper."""

    def setup_method(self):
        USER_REGISTRY.clear()

    def teardown_method(self):
        USER_REGISTRY.clear()

    def test_unknown_user_defaults_to_default(self):
        assert get_user_type("somebody") == UserType.DEFAULT

    def test_registered_admin(self):
        USER_REGISTRY["alice"] = UserType.ADMIN
        assert get_user_type("alice") == UserType.ADMIN

    def test_registered_guest(self):
        USER_REGISTRY["bob"] = UserType.GUEST
        assert get_user_type("bob") == UserType.GUEST

    def test_registered_default(self):
        USER_REGISTRY["carol"] = UserType.DEFAULT
        assert get_user_type("carol") == UserType.DEFAULT


class TestMyDeps:
    """Test that MyDeps includes username and user_type fields."""

    def test_default_user_type_is_default(self):
        deps = MyDeps()
        assert deps.user_type == UserType.DEFAULT
        assert deps.username is None

    def test_custom_user_type_and_username(self):
        deps = MyDeps(username="alice", user_type=UserType.ADMIN)
        assert deps.username == "alice"
        assert deps.user_type == UserType.ADMIN

    def test_guest_user_type(self):
        deps = MyDeps(username="guest_user", user_type=UserType.GUEST)
        assert deps.user_type == UserType.GUEST
