"""Unit tests for src/models/schemas.py."""

from src.models.schemas import (
    UserType,
    GUEST_ALLOWED_TOOLS,
    get_user_type_from_discord_roles,
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


class TestGetUserTypeFromDiscordRoles:
    """Test the get_user_type_from_discord_roles helper."""

    def test_no_roles_defaults_to_default(self):
        assert get_user_type_from_discord_roles([]) == UserType.DEFAULT

    def test_unrelated_roles_default_to_default(self):
        assert (
            get_user_type_from_discord_roles(["member", "booster"]) == UserType.DEFAULT
        )

    def test_admin_role_returns_admin(self):
        assert get_user_type_from_discord_roles(["admin"]) == UserType.ADMIN

    def test_admin_role_case_insensitive(self):
        assert get_user_type_from_discord_roles(["Admin"]) == UserType.ADMIN
        assert get_user_type_from_discord_roles(["ADMIN"]) == UserType.ADMIN

    def test_guest_role_returns_guest(self):
        assert get_user_type_from_discord_roles(["guest"]) == UserType.GUEST

    def test_guest_role_case_insensitive(self):
        assert get_user_type_from_discord_roles(["Guest"]) == UserType.GUEST

    def test_admin_takes_priority_over_guest(self):
        assert get_user_type_from_discord_roles(["guest", "admin"]) == UserType.ADMIN

    def test_admin_with_other_roles(self):
        assert (
            get_user_type_from_discord_roles(["member", "Admin", "booster"])
            == UserType.ADMIN
        )

    def test_guest_with_other_roles(self):
        assert get_user_type_from_discord_roles(["member", "Guest"]) == UserType.GUEST


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
