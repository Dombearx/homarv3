"""Lichess chess agent for managing chess move rules and interacting with Lichess API."""

import json
import os
from pathlib import Path

import httpx
from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

LICHESS_API_BASE = "https://lichess.org/api"

CHESS_RULES_FILE = Path(os.getenv("CHESS_RULES_FILE", "/data/chess_rules.json"))

LICHESS_AGENT_PROMPT = """
You are an interface to Lichess, the online chess platform.

You can:
1. Manage chess move rules - each rule defines what move to make when the opponent plays a specific move.
   Rules are stored persistently and checked when monitoring a game.
2. Retrieve information about ongoing Lichess games.
3. Execute moves in an ongoing Lichess game.
4. Check whether any saved rules apply to the current game state and execute the appropriate response.

Guidelines:
- Moves should be in UCI notation (e.g. "e2e4", "b1c3", "g8f6").
- When adding a rule, always store a human-readable description so rules are easy to review.
- When checking and applying rules, report every game checked and what happened.

As a response, briefly summarize what you have done.
Do not ask follow-up questions.
"""

settings = OpenAIResponsesModelSettings(
    openai_reasoning_effort="minimal",
    openai_reasoning_summary="concise",
)

lichess_agent = Agent(
    "openai:gpt-5-mini",
    instructions=LICHESS_AGENT_PROMPT,
    model_settings=settings,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_headers() -> dict:
    """Return Lichess API request headers with Bearer token authorization."""
    token = os.getenv("LICHESS_TOKEN")
    if not token:
        raise ValueError("LICHESS_TOKEN environment variable is not set")
    return {"Authorization": f"Bearer {token}"}


def _load_rules() -> list[dict]:
    """Load chess rules from the JSON file. Returns an empty list on any error."""
    if not CHESS_RULES_FILE.exists():
        return []
    try:
        with open(CHESS_RULES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading chess rules: {e}")
        return []


def _save_rules(rules: list[dict]) -> None:
    """Persist chess rules to the JSON file."""
    try:
        CHESS_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CHESS_RULES_FILE, "w") as f:
            json.dump(rules, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving chess rules: {e}")
        raise


def _fetch_ongoing_games() -> list[dict]:
    """Fetch the list of ongoing games from the Lichess API."""
    headers = _get_headers()
    response = httpx.get(
        f"{LICHESS_API_BASE}/account/playing",
        headers=headers,
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json().get("nowPlaying", [])


# ---------------------------------------------------------------------------
# Rule management tools
# ---------------------------------------------------------------------------


@lichess_agent.tool_plain
def add_chess_rule(opponent_move: str, our_move: str, description: str) -> str:
    """Add a chess move rule: when the opponent plays *opponent_move*, respond with *our_move*.

    Args:
        opponent_move: Opponent's trigger move in UCI notation (e.g. "b1c3").
        our_move: Our response move in UCI notation (e.g. "d7d5").
        description: Human-readable description (e.g. "If opponent moves knight to c3, push pawn to d5").

    Returns:
        Confirmation or error message.
    """
    rules = _load_rules()

    normalized_opp = opponent_move.lower().strip()
    for rule in rules:
        if rule["opponent_move"] == normalized_opp:
            return (
                f"A rule for opponent move '{opponent_move}' already exists. "
                "Remove it first if you want to update it."
            )

    rule = {
        "opponent_move": normalized_opp,
        "our_move": our_move.lower().strip(),
        "description": description,
    }
    rules.append(rule)
    _save_rules(rules)

    return (
        f"Rule added: {description} (trigger: {opponent_move} → response: {our_move})"
    )


@lichess_agent.tool_plain
def list_chess_rules() -> str:
    """List all stored chess move rules.

    Returns:
        Formatted list of all rules, or a message if none exist.
    """
    rules = _load_rules()
    if not rules:
        return "No chess rules stored yet."

    lines = [f"Stored chess rules ({len(rules)}):"]
    for i, rule in enumerate(rules, 1):
        lines.append(
            f"\n{i}. {rule['description']}\n"
            f"   Opponent plays: {rule['opponent_move']} → We respond: {rule['our_move']}"
        )
    return "\n".join(lines)


@lichess_agent.tool_plain
def remove_chess_rule(rule_index: int) -> str:
    """Remove a chess move rule by its 1-based index (as shown by list_chess_rules).

    Args:
        rule_index: 1-based index of the rule to remove.

    Returns:
        Confirmation or error message.
    """
    rules = _load_rules()
    if not rules:
        return "No chess rules to remove."
    if rule_index < 1 or rule_index > len(rules):
        return f"Invalid index {rule_index}. Valid range: 1–{len(rules)}."

    removed = rules.pop(rule_index - 1)
    _save_rules(rules)
    return f"Removed rule: {removed['description']}"


@lichess_agent.tool_plain
def clear_chess_rules() -> str:
    """Remove all stored chess move rules.

    Returns:
        Confirmation message with the number of rules deleted.
    """
    rules = _load_rules()
    count = len(rules)
    _save_rules([])
    return f"Cleared all {count} chess rule(s)."


# ---------------------------------------------------------------------------
# Lichess API tools
# ---------------------------------------------------------------------------


@lichess_agent.tool_plain
def get_current_games() -> str:
    """Get all currently ongoing Lichess games for the authenticated user.

    Returns:
        Formatted information about ongoing games, or a message if none are found.
    """
    try:
        games = _fetch_ongoing_games()
        if not games:
            return "No ongoing games."

        lines = [f"Ongoing games ({len(games)}):"]
        for game in games:
            opponent = game.get("opponent", {})
            lines.append(
                f"\nGame ID: {game['gameId']}\n"
                f"  Opponent: {opponent.get('username', 'Unknown')}\n"
                f"  Color: {game.get('color', 'Unknown')}\n"
                f"  My turn: {game.get('isMyTurn', False)}\n"
                f"  Last move: {game.get('lastMove') or 'None'}\n"
                f"  URL: https://lichess.org/{game['gameId']}"
            )
        return "\n".join(lines)

    except ValueError as e:
        return f"Configuration error: {e}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching ongoing games: {e}")
        return f"Error fetching games: {e}"
    except Exception as e:
        logger.error(f"Unexpected error fetching ongoing games: {e}")
        return f"Error fetching games: {e}"


@lichess_agent.tool_plain
def execute_move(game_id: str, move: str) -> str:
    """Execute a chess move in a Lichess game.

    Args:
        game_id: The Lichess game ID.
        move: The move to play in UCI notation (e.g. "e2e4").

    Returns:
        Confirmation or error message.
    """
    try:
        headers = _get_headers()
        response = httpx.post(
            f"{LICHESS_API_BASE}/board/game/{game_id}/move/{move}",
            headers=headers,
            timeout=10.0,
        )
        response.raise_for_status()
        return f"Move '{move}' executed successfully in game {game_id}."

    except ValueError as e:
        return f"Configuration error: {e}"
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            return f"Invalid move '{move}': {e.response.text}"
        logger.error(f"HTTP error executing move: {e}")
        return f"Error executing move: {e}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error executing move: {e}")
        return f"Error executing move: {e}"
    except Exception as e:
        logger.error(f"Unexpected error executing move: {e}")
        return f"Error executing move: {e}"


@lichess_agent.tool_plain
def check_and_apply_rules(game_id: str = "") -> str:
    """Check the current game state and apply saved rules if the opponent made a matching move.

    For each ongoing game (or a specific game if *game_id* is given):
    1. Skip if it is not our turn.
    2. Compare the opponent's last move against every stored rule.
    3. If a rule matches, execute the configured response move.

    This function can be called manually or scheduled every 20 minutes via the
    send_delayed_message tool.

    Args:
        game_id: Optional Lichess game ID to restrict the check to one game.
                 Pass an empty string (or omit) to check all ongoing games.

    Returns:
        Summary of what happened for each game checked.
    """
    try:
        rules = _load_rules()
        if not rules:
            return "No chess rules configured. Add rules first with add_chess_rule."

        games = _fetch_ongoing_games()
        if not games:
            return "No ongoing games to check."

        if game_id:
            games = [g for g in games if g["gameId"] == game_id]
            if not games:
                return f"Game '{game_id}' not found among ongoing games."

        results: list[str] = []
        for game in games:
            gid = game["gameId"]

            if not game.get("isMyTurn", False):
                results.append(f"Game {gid}: Not my turn – skipping.")
                continue

            last_move = (game.get("lastMove") or "").lower().strip()
            if not last_move:
                results.append(f"Game {gid}: No moves played yet.")
                continue

            matched = False
            for rule in rules:
                if rule["opponent_move"] == last_move:
                    move_result = execute_move(gid, rule["our_move"])
                    results.append(
                        f"Game {gid}: Rule matched — '{rule['description']}'. "
                        f"Executed '{rule['our_move']}'. {move_result}"
                    )
                    matched = True
                    break

            if not matched:
                results.append(
                    f"Game {gid}: Opponent played '{last_move}' – no matching rule found."
                )

        return "\n".join(results) if results else "No games processed."

    except ValueError as e:
        return f"Configuration error: {e}"
    except httpx.HTTPError as e:
        logger.error(f"HTTP error in check_and_apply_rules: {e}")
        return f"Error checking rules: {e}"
    except Exception as e:
        logger.error(f"Unexpected error in check_and_apply_rules: {e}")
        return f"Error checking rules: {e}"
