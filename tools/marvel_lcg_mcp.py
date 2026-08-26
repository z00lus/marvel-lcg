#!/usr/bin/env python3
"""Minimal stdio MCP server for a running Ronin Edition engine.

The process uses only Python's standard library.  It translates MCP tool calls
into the authenticated JSON endpoints under ``/api/agent``; no HTML, DOM or
WebSocket client is involved.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


SERVER_NAME = "marvel-lcg"
SERVER_VERSION = "0.2.0"
PROTOCOL_VERSION = "2024-11-05"
DEFAULT_DECISION_WAIT_MS = 2000


class AgentHttpClient:
    def __init__(self) -> None:
        self.base_url = os.environ.get(
            "MARVEL_LCG_URL", "http://127.0.0.1:2345"
        ).rstrip("/")
        self.password = os.environ.get("MARVEL_LCG_PASSWORD", "")
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )
        self.authenticated = False

    def _authenticate(self) -> None:
        if self.authenticated or not self.password:
            self.authenticated = True
            return
        request = urllib.request.Request(
            f"{self.base_url}/authenticate",
            data=json.dumps({"password": self.password}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.opener.open(request, timeout=15) as response:
            response.read()
        self.authenticated = True

    def post(self, path: str, data: dict[str, Any] | None = None,
             timeout: float = 35) -> dict[str, Any]:
        self._authenticate()
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(data or {}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                details = json.loads(raw.decode("utf-8"))
                message = details.get("error") or str(details)
            except Exception:
                message = raw.decode("utf-8", "replace") or str(exc)
            raise RuntimeError(f"Engine HTTP {exc.code}: {message}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach the Marvel LCG server at {self.base_url}: {exc.reason}"
            ) from exc
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))


CLIENT = AgentHttpClient()


def _card(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": card.get("id"),
        "name": card.get("name"),
        "card_id": card.get("card_id"),
        "type": card.get("card_type"),
        "ready": card.get("is_ready"),
        "face_up": card.get("is_face_up"),
        "bound_to": card.get("bind_object_id") or None,
        "cost": card.get("cost"),
        "info": card.get("info") or {},
        "traits": sorted((card.get("traits") or {}).keys()),
        "effects": card.get("effects") or [],
        "resources": card.get("resources") or [],
    }


def _zone(cards: Any) -> list[dict[str, Any]]:
    return [_card(card) for card in (cards or []) if isinstance(card, dict)]


def _compact_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    world = snapshot.get("world") or {}
    players = world.get("players") or []
    player = players[0] if players else {}

    player_zones = {
        "hero_area": _zone(player.get("area_hero")),
        "hand": _zone(player.get("hand_cards")),
        "allies": _zone(player.get("allies")),
        "supports": _zone(player.get("supports")),
        "engaged_minions": _zone(player.get("engaged_enemies")),
        "obligations": _zone(player.get("obligations_area")),
        "environment": _zone(player.get("environment_area")),
        "discard": _zone(player.get("player_discard_pile")),
        "additional_deck": _zone(player.get("additional_deck")),
        "additional_discard": _zone(player.get("additional_discard_pile")),
        "special_decks": {
            name: _zone(cards)
            for name, cards in (player.get("special_decks") or {}).items()
        },
        "resources": player.get("resources", ""),
        "deck_count": len(player.get("player_deck") or []),
        "discard_count": len(player.get("player_discard_pile") or []),
    }
    scenario_zones = {
        "villain_area": _zone(world.get("area_villain")),
        "main_schemes": _zone(world.get("area_schemes_main")),
        "side_schemes": _zone(world.get("area_schemes_side")),
        "environment": _zone(world.get("area_environment")),
        "evidence": _zone(world.get("area_evidence")),
        "mission": _zone(world.get("area_mission")),
        "rules": _zone(world.get("area_rule")),
        "boost_cards": _zone(world.get("area_boost")),
        "additional_decks": [
            _zone(cards) for cards in (world.get("additional_decks") or [])
        ],
        "additional_discards": [
            _zone(cards) for cards in (world.get("additional_discard_piles") or [])
        ],
        "encounter_discard": _zone(world.get("encounter_discard_pile")),
        "encounter_deck_count": len(world.get("encounter_deck") or []),
        "processing": _zone(world.get("area_processing")),
        "revealing": _zone(world.get("area_revealing")),
    }

    # Index the full descriptor, including temporarily exposed cards from deck
    # searches.  The compact board stays small, but legal targets and payment
    # sources still get readable names in uncommon selection windows.
    all_cards: dict[int, dict[str, Any]] = {}

    def index_cards(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("id") is not None and "card_id" in value:
                all_cards[int(value["id"])] = _card(value)
            for nested in value.values():
                index_cards(nested)
        elif isinstance(value, list):
            for nested in value:
                index_cards(nested)

    index_cards(world)

    resource_owner: dict[int, dict[str, Any]] = {}
    for card in all_cards.values():
        for effect_id in card.get("resources") or []:
            resource_owner[int(effect_id)] = {
                "card_id": card.get("id"),
                "card": card.get("name"),
            }

    raw_prompt = snapshot.get("prompt")
    prompt = None
    if raw_prompt:
        options = []
        for option in raw_prompt.get("options") or []:
            legal_targets = []
            for target_id in option.get("all_legal_targets") or []:
                target = all_cards.get(int(target_id), {})
                legal_targets.append({
                    "id": target_id,
                    "name": target.get("name", "unknown"),
                    "card_id": target.get("card_id", ""),
                })
            payments = {}
            for target_id, payment in (option.get("target_payment") or {}).items():
                candidates = []
                for candidate in payment.get("payment") or []:
                    for effect_id, resource in candidate.items():
                        owner = resource_owner.get(int(effect_id), {})
                        candidates.append({
                            "effect_id": int(effect_id),
                            "resource": resource,
                            **owner,
                        })
                payments[str(target_id)] = {
                    "cost": payment.get("cost", ""),
                    "rules": payment.get("rule") or [],
                    "candidates": candidates,
                }
            bind = all_cards.get(int(option.get("bind_id", 0)), {})
            options.append({
                "effect_id": option.get("id"),
                "name": option.get("name"),
                "source": bind.get("name", "unknown"),
                "source_card_id": bind.get("card_id", ""),
                "target_range": option.get("target_num_range") or [0, 0],
                "legal_targets": legal_targets,
                "payments": payments,
                "failure_reason": option.get("failure_reason") or "",
                "select_rule": option.get("select_rule") or "",
            })
        prompt = {
            "revision": raw_prompt.get("revision"),
            "type": raw_prompt.get("ability_type"),
            "event": raw_prompt.get("event_name"),
            "text": raw_prompt.get("prompt_text"),
            "can_skip": raw_prompt.get("show_cancel"),
            "options": options,
        }

    return {
        "status": snapshot.get("status"),
        "game_id": snapshot.get("game_id"),
        "step": snapshot.get("step"),
        "round": world.get("round_id"),
        "phase": world.get("phase"),
        "event": world.get("event_name"),
        "last_message": world.get("prompt_last_text"),
        "outcome": snapshot.get("outcome"),
        "recent_log": snapshot.get("recent_log") or [],
        "player": player_zones,
        "scenario": scenario_zones,
        "prompt": prompt,
    }


TOOLS = [
    {
        "name": "catalog",
        "description": "List hero decks, scenarios, expert availability, and required underlings.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "start_game",
        "description": "Start a new one-hero Rules 1.8 game, replace the previous active session, and return the first decision.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hero": {"type": "string", "description": "Hero deck id from catalog"},
                "scenario": {"type": "string", "description": "Scenario id from catalog"},
                "expert": {"type": "boolean", "default": False},
                "underling": {"type": "string", "description": "Required only by scenarios that list underlings"},
                "seed": {"type": "integer", "default": -1},
            },
            "required": ["hero", "scenario"],
            "additionalProperties": False,
        },
    },
    {
        "name": "continue_game",
        "description": "Attach headlessly, continue the server's active saved game, and return its next decision.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "observe",
        "description": "Read the board, recent rules log, and current legal prompt. Can long-poll for a changed step/prompt.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "since_revision": {"type": "integer"},
                "since_step": {"type": "integer"},
                "wait_ms": {"type": "integer", "minimum": 0, "maximum": 30000, "default": 2000},
                "detail": {"type": "string", "enum": ["summary", "full"], "default": "summary"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "act",
        "description": "Submit one current legal effect and return the next decision. Use the current prompt revision.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "revision": {"type": "integer"},
                "effect_id": {"type": "integer"},
                "targets": {"type": "array", "items": {"type": "integer"}, "default": []},
                "resources": {"type": "array", "items": {"type": "integer"}, "default": []},
                "wait_ms": {"type": "integer", "minimum": 0, "maximum": 30000, "default": 2000},
            },
            "required": ["revision", "effect_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "skip",
        "description": "Decline an optional prompt and return the next decision. Forced prompts cannot be skipped.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "revision": {"type": "integer"},
                "wait_ms": {"type": "integer", "minimum": 0, "maximum": 30000, "default": 2000},
            },
            "required": ["revision"],
            "additionalProperties": False,
        },
    },
    {
        "name": "save_replay",
        "description": "Save the current game inputs as a replay and return its server path.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "disconnect",
        "description": "Release the virtual headless player after a game or investigation.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "catalog":
        return CLIENT.post("/api/agent/catalog")
    if name == "start_game":
        payload = {
            "player_id": 0,
            "wait_ms": DEFAULT_DECISION_WAIT_MS,
            **arguments,
        }
        return _compact_snapshot(CLIENT.post("/api/agent/start", payload, timeout=10))
    if name == "continue_game":
        snapshot = CLIENT.post("/api/agent/continue", {
            "player_id": 0,
            "wait_ms": DEFAULT_DECISION_WAIT_MS,
        }, timeout=10)
        return _compact_snapshot(snapshot)
    if name == "observe":
        detail = arguments.get("detail", "summary")
        payload = {key: value for key, value in arguments.items() if key != "detail"}
        payload["player_id"] = 0
        snapshot = CLIENT.post(
            "/api/agent/observe", payload,
            timeout=max(35, (int(payload.get("wait_ms", 0)) / 1000) + 5),
        )
        return snapshot if detail == "full" else _compact_snapshot(snapshot)
    if name == "act":
        payload = {
            "player_id": 0,
            "wait_ms": DEFAULT_DECISION_WAIT_MS,
            **arguments,
        }
        wait_ms = int(payload.get("wait_ms", DEFAULT_DECISION_WAIT_MS))
        snapshot = CLIENT.post(
            "/api/agent/act", payload, timeout=max(10, wait_ms / 1000 + 5),
        )
        return _compact_snapshot(snapshot)
    if name == "skip":
        wait_ms = int(arguments.get("wait_ms", DEFAULT_DECISION_WAIT_MS))
        snapshot = CLIENT.post("/api/agent/act", {
            "player_id": 0,
            "revision": arguments["revision"],
            "effect_id": 0,
            "targets": [],
            "resources": [],
            "wait_ms": wait_ms,
        }, timeout=max(10, wait_ms / 1000 + 5))
        return _compact_snapshot(snapshot)
    if name == "save_replay":
        return CLIENT.post("/api/agent/save-replay")
    if name == "disconnect":
        return CLIENT.post("/api/agent/disconnect", {"player_id": 0})
    raise ValueError(f"Unknown tool: {name}")


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None

    if method == "initialize":
        requested = (message.get("params") or {}).get("protocolVersion")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": requested or PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        try:
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, indent=2, ensure_ascii=False),
                    }],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            }
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> int:
    for raw_line in sys.stdin:
        if not raw_line.strip():
            continue
        try:
            message = json.loads(raw_line)
            response = handle(message)
        except Exception as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        if response is not None:
            send(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
