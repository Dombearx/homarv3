"""Unit tests for lichess_agent.py module."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

from src.agents_as_tools.lichess_agent import (
    add_chess_rule,
    list_chess_rules,
    remove_chess_rule,
    clear_chess_rules,
    get_current_games,
    execute_move,
    check_and_apply_rules,
    _load_rules,
    _save_rules,
    _get_headers,
    _fetch_ongoing_games,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(
    game_id: str = "abc123",
    is_my_turn: bool = True,
    last_move: str = "b1c3",
    color: str = "black",
    opponent_name: str = "opponent",
) -> dict:
    return {
        "gameId": game_id,
        "isMyTurn": is_my_turn,
        "lastMove": last_move,
        "color": color,
        "opponent": {"username": opponent_name},
    }


# ---------------------------------------------------------------------------
# _get_headers
# ---------------------------------------------------------------------------


class TestGetHeaders:
    def test_returns_authorization_header_when_token_set(self, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "mytoken")
        headers = _get_headers()
        assert headers["Authorization"] == "Bearer mytoken"

    def test_raises_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("LICHESS_TOKEN", raising=False)
        with pytest.raises(ValueError, match="LICHESS_TOKEN"):
            _get_headers()


# ---------------------------------------------------------------------------
# _load_rules / _save_rules
# ---------------------------------------------------------------------------


class TestLoadSaveRules:
    def test_load_returns_empty_list_when_file_missing(self, tmp_path, monkeypatch):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "no_file.json"
        try:
            result = _load_rules()
            assert result == []
        finally:
            mod.CHESS_RULES_FILE = original

    def test_save_and_load_roundtrip(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            rules = [
                {
                    "opponent_move": "b1c3",
                    "our_move": "d7d5",
                    "description": "Test rule",
                }
            ]
            _save_rules(rules)
            loaded = _load_rules()
            assert loaded == rules
        finally:
            mod.CHESS_RULES_FILE = original

    def test_load_returns_empty_list_on_invalid_json(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        rules_file = tmp_path / "bad.json"
        rules_file.write_text("not valid json")

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = rules_file
        try:
            result = _load_rules()
            assert result == []
        finally:
            mod.CHESS_RULES_FILE = original


# ---------------------------------------------------------------------------
# add_chess_rule
# ---------------------------------------------------------------------------


class TestAddChessRule:
    def test_adds_new_rule(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            result = add_chess_rule("b1c3", "d7d5", "Knight c3 → pawn d5")
            assert "added" in result.lower()
            rules = _load_rules()
            assert len(rules) == 1
            assert rules[0]["opponent_move"] == "b1c3"
            assert rules[0]["our_move"] == "d7d5"
        finally:
            mod.CHESS_RULES_FILE = original

    def test_rejects_duplicate_opponent_move(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "First rule")
            result = add_chess_rule("b1c3", "e7e5", "Duplicate rule")
            assert "already exists" in result
            assert len(_load_rules()) == 1
        finally:
            mod.CHESS_RULES_FILE = original

    def test_normalizes_move_to_lowercase(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("B1C3", "D7D5", "Upper case input")
            rules = _load_rules()
            assert rules[0]["opponent_move"] == "b1c3"
            assert rules[0]["our_move"] == "d7d5"
        finally:
            mod.CHESS_RULES_FILE = original


# ---------------------------------------------------------------------------
# list_chess_rules
# ---------------------------------------------------------------------------


class TestListChessRules:
    def test_returns_message_when_no_rules(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            result = list_chess_rules()
            assert "No chess rules" in result
        finally:
            mod.CHESS_RULES_FILE = original

    def test_lists_all_rules(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Rule one")
            add_chess_rule("g1f3", "e7e5", "Rule two")
            result = list_chess_rules()
            assert "Rule one" in result
            assert "Rule two" in result
            assert "b1c3" in result
            assert "g1f3" in result
        finally:
            mod.CHESS_RULES_FILE = original


# ---------------------------------------------------------------------------
# remove_chess_rule
# ---------------------------------------------------------------------------


class TestRemoveChessRule:
    def test_removes_rule_by_index(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Rule to remove")
            result = remove_chess_rule(1)
            assert "Removed" in result
            assert len(_load_rules()) == 0
        finally:
            mod.CHESS_RULES_FILE = original

    def test_returns_error_for_invalid_index(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Rule")
            result = remove_chess_rule(99)
            assert "Invalid" in result
        finally:
            mod.CHESS_RULES_FILE = original

    def test_returns_error_when_no_rules(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            result = remove_chess_rule(1)
            assert "No chess rules" in result
        finally:
            mod.CHESS_RULES_FILE = original


# ---------------------------------------------------------------------------
# clear_chess_rules
# ---------------------------------------------------------------------------


class TestClearChessRules:
    def test_clears_all_rules(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Rule 1")
            add_chess_rule("g1f3", "e7e5", "Rule 2")
            result = clear_chess_rules()
            assert "2" in result
            assert len(_load_rules()) == 0
        finally:
            mod.CHESS_RULES_FILE = original

    def test_clear_empty_list_returns_zero(self, tmp_path):
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            result = clear_chess_rules()
            assert "0" in result
        finally:
            mod.CHESS_RULES_FILE = original


# ---------------------------------------------------------------------------
# get_current_games
# ---------------------------------------------------------------------------


class TestGetCurrentGames:
    @patch("src.agents_as_tools.lichess_agent.httpx.get")
    def test_returns_game_info_on_success(self, mock_get, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "nowPlaying": [_make_game("game1", last_move="e2e4")]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_current_games()

        assert "game1" in result
        assert "e2e4" in result

    @patch("src.agents_as_tools.lichess_agent.httpx.get")
    def test_returns_message_when_no_games(self, mock_get, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        mock_response = MagicMock()
        mock_response.json.return_value = {"nowPlaying": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = get_current_games()

        assert "No ongoing games" in result

    @patch("src.agents_as_tools.lichess_agent.httpx.get")
    def test_returns_error_on_http_failure(self, mock_get, monkeypatch):
        import httpx

        monkeypatch.setenv("LICHESS_TOKEN", "token")
        mock_get.side_effect = httpx.HTTPError("Connection error")

        result = get_current_games()

        assert "Error" in result

    def test_returns_config_error_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("LICHESS_TOKEN", raising=False)
        result = get_current_games()
        assert "Configuration error" in result or "LICHESS_TOKEN" in result


# ---------------------------------------------------------------------------
# execute_move
# ---------------------------------------------------------------------------


class TestExecuteMove:
    @patch("src.agents_as_tools.lichess_agent.httpx.post")
    def test_executes_move_successfully(self, mock_post, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = execute_move("game1", "e2e4")

        assert "e2e4" in result
        assert "game1" in result

    @patch("src.agents_as_tools.lichess_agent.httpx.post")
    def test_returns_error_on_invalid_move(self, mock_post, monkeypatch):
        import httpx

        monkeypatch.setenv("LICHESS_TOKEN", "token")
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Illegal move"
        mock_post.side_effect = httpx.HTTPStatusError(
            "400", request=MagicMock(), response=mock_response
        )

        result = execute_move("game1", "zzz0")

        assert "Invalid move" in result or "Error" in result

    def test_returns_config_error_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("LICHESS_TOKEN", raising=False)
        result = execute_move("game1", "e2e4")
        assert "Configuration error" in result or "LICHESS_TOKEN" in result


# ---------------------------------------------------------------------------
# check_and_apply_rules
# ---------------------------------------------------------------------------


class TestCheckAndApplyRules:
    @patch("src.agents_as_tools.lichess_agent.execute_move")
    @patch("src.agents_as_tools.lichess_agent._fetch_ongoing_games")
    def test_applies_matching_rule(
        self, mock_fetch, mock_execute, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Knight to c3 → pawn to d5")
            mock_fetch.return_value = [
                _make_game("game1", is_my_turn=True, last_move="b1c3")
            ]
            mock_execute.return_value = "Move executed."

            result = check_and_apply_rules()

            assert "d7d5" in result
            assert "Knight to c3" in result
            mock_execute.assert_called_once_with("game1", "d7d5")
        finally:
            mod.CHESS_RULES_FILE = original

    @patch("src.agents_as_tools.lichess_agent._fetch_ongoing_games")
    def test_skips_game_when_not_my_turn(self, mock_fetch, tmp_path, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Knight to c3")
            mock_fetch.return_value = [
                _make_game("game1", is_my_turn=False, last_move="b1c3")
            ]

            result = check_and_apply_rules()

            assert "Not my turn" in result
        finally:
            mod.CHESS_RULES_FILE = original

    @patch("src.agents_as_tools.lichess_agent._fetch_ongoing_games")
    def test_reports_no_matching_rule(self, mock_fetch, tmp_path, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Knight to c3")
            mock_fetch.return_value = [
                _make_game("game1", is_my_turn=True, last_move="g1f3")
            ]

            result = check_and_apply_rules()

            assert "no matching rule" in result.lower()
        finally:
            mod.CHESS_RULES_FILE = original

    @patch("src.agents_as_tools.lichess_agent._fetch_ongoing_games")
    def test_filters_by_game_id(self, mock_fetch, tmp_path, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Rule")
            mock_fetch.return_value = [
                _make_game("game1", is_my_turn=True, last_move="b1c3"),
                _make_game("game2", is_my_turn=True, last_move="b1c3"),
            ]

            result = check_and_apply_rules("nonexistent")

            assert "not found" in result.lower()
        finally:
            mod.CHESS_RULES_FILE = original

    @patch("src.agents_as_tools.lichess_agent._fetch_ongoing_games")
    def test_returns_message_when_no_rules(self, mock_fetch, tmp_path, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            mock_fetch.return_value = [_make_game()]

            result = check_and_apply_rules()

            assert "No chess rules" in result
        finally:
            mod.CHESS_RULES_FILE = original

    @patch("src.agents_as_tools.lichess_agent._fetch_ongoing_games")
    def test_returns_message_when_no_games(self, mock_fetch, tmp_path, monkeypatch):
        monkeypatch.setenv("LICHESS_TOKEN", "token")
        import src.agents_as_tools.lichess_agent as mod

        original = mod.CHESS_RULES_FILE
        mod.CHESS_RULES_FILE = tmp_path / "rules.json"
        try:
            add_chess_rule("b1c3", "d7d5", "Rule")
            mock_fetch.return_value = []

            result = check_and_apply_rules()

            assert "No ongoing games" in result
        finally:
            mod.CHESS_RULES_FILE = original
