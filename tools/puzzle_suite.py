#!/usr/bin/env python3
"""Run the puzzle regression suite: boot a fresh engine per case, drive it, assert.

Why this exists: `replays/min_test/` is empty (the maintainer cannot share the
corpus) and there is no CI, so an engine change — a new keyword, a payment-path
fix — can silently break any of ~3,480 card scripts with nothing to catch it.
These cases pin behaviour that was verified by hand once, so it stays verified.

**Assert on board state, never on the absence of errors.** The engine does not log
ability failures to stdout, and a wrong-argument-type handler can fail with no
exception, no crash file and no client error (this is exactly how `58028` shipped
broken). Board state is the only signal that catches it.

A case is an ordinary puzzle file with a few extra keys. `Json.ConvertDictToDataclass`
filters to declared fields, so the engine ignores them and the file still loads:

    "driver": ["--steps", "40", "--greedy"]      # headless_client.py args
    "expect": {"hero_hp": 10, "attack_prompts": 2}
    "xfail":  "reason"                           # known gap; failing is the pass
    "note":   "prose: what this pins and why"    # stripped from the payload

Put prose in `note`, never in `comment`: the engine keeps `comment`, so it reaches
the query string, and no value there may contain a space (see boot()).

`driver` may instead be a list of lists — phases run in order against the same
server. Use phases whenever the assertion depends on *ordering*: a single strategy
cannot express "play your cards, then attack", because --greedy takes the last
option at every prompt and where the attack lands is unpinned. An expectation
resting on that is a coin flip, not a test.

Cases live in tests/regression/<pack>/, NOT under puzzle/. Two reasons: `puzzle/`
is untracked in this repo (`.git/info/exclude`, and upstream never shipped it), so
cases put there would silently never be committed; and that exclude is unanchored,
so it swallows a `puzzle` directory at any depth — `tests/puzzle/` was caught too.
Nothing is lost by living outside `puzzle/`: the runner POSTs each case inline to
`/new_puzzle`, so the engine never reads them from disk, and keeping them out of
the puzzle browser is desirable anyway — most are one-move states that would only
confuse a human looking for something to play.

Usage:
  python3 tools/puzzle_suite.py                 # all cases
  python3 tools/puzzle_suite.py -k overpay      # filter by name
  python3 tools/puzzle_suite.py -v              # show driver output on failure
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES_DIR = ROOT / "tests" / "regression"
_VENV_PY = ROOT / ".venv" / "bin" / "python"
PY = str(_VENV_PY) if _VENV_PY.exists() else sys.executable
BASE = "http://127.0.0.1:2345"
PORT = 2345

_cookie: str | None = None


def cookie() -> str:
    """The `app_version` cookie every request needs, read from the server.

    Hardcoding the version is what silently broke this harness once already:
    every path answers with the same version-mismatch interstitial when the
    cookie disagrees with `Ver.ui_version_str`, so the failure surfaces as a
    websocket handshake error or an empty board rather than as "wrong version".
    `/get_version` is registered with `need_auth=False, need_check_version=False`
    precisely so it can be read before the cookie is known.
    """
    global _cookie
    if _cookie is None:
        with urllib.request.urlopen(f"{BASE}/get_version", timeout=20) as r:
            version = r.read().decode("utf-8").strip()
        if not version:
            raise RuntimeError("/get_version returned nothing")
        _cookie = f"app_version={version}"
    return _cookie


def can_bind() -> bool:
    """The engine asserts IsPortAvailable with a bare bind() and no SO_REUSEADDR,
    so lsof going quiet is not enough — test it the same way it does."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", PORT))
        return True
    except OSError:
        return False
    finally:
        s.close()


def free_port(timeout: int = 25) -> None:
    subprocess.run(f"lsof -ti TCP:{PORT} | xargs kill 2>/dev/null", shell=True)
    for _ in range(timeout):
        if can_bind():
            return
        time.sleep(1)
    subprocess.run(f"lsof -ti TCP:{PORT} | xargs kill -9 2>/dev/null", shell=True)
    for _ in range(timeout):
        if can_bind():
            return
        time.sleep(1)


def get(path: str, timeout: int = 20) -> str:
    """GET an engine endpoint.

    Two non-obvious requirements: the `app_version` cookie, without which every
    path returns the same interstitial HTML; and gzip, which the server sends
    regardless (this is why curl needs `--compressed`). urllib does not
    decompress on its own, so a raw read yields bytes that fail JSON parsing at
    char 0 — which looks like an empty response rather than a decoding problem.
    """
    req = urllib.request.Request(
        f"{BASE}{path}",
        headers={"Cookie": cookie(), "Accept-Encoding": "gzip, identity"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
            import gzip
            raw = gzip.decompress(raw)
    return raw.decode("utf-8", "replace")


def boot(case_json: dict, log_path: pathlib.Path) -> subprocess.Popen | None:
    global _cookie
    _cookie = None
    free_port()
    for stale in ("crash.json", "crash.log"):
        (ROOT / stale).unlink(missing_ok=True)
    log = open(log_path, "w")
    proc = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=log, stderr=log)
    for _ in range(40):
        if not can_bind():           # something is listening
            break
        if proc.poll() is not None:
            return None
        time.sleep(1)
    else:
        return None
    # The engine only builds a world once a puzzle is loaded, and `/new_puzzle`
    # reads the query string RAW — it is never percent-decoded. So the payload
    # must contain no spaces anywhere, including inside string values: compact
    # separators are not enough, a `"comment": "two words"` breaks the request.
    # Fail loudly here, because the alternative is 15 opaque "could not read
    # world" cascades that say nothing about the real cause.
    # `note` is stripped alongside the runner's own keys so a case can carry prose
    # explaining what it pins and why. `comment` cannot: the engine keeps it, so it
    # goes into the payload and must stay space-free like every other value.
    payload = json.dumps({k: v for k, v in case_json.items()
                          if k not in ("driver", "expect", "xfail", "note")},
                         separators=(",", ":"))
    if " " in payload:
        offenders = [f"{k}={v!r}" for k, v in case_json.items()
                     if isinstance(v, str) and " " in v]
        print(f"    payload contains a space — /new_puzzle takes the query string "
              f"raw, so every value must be space-free. Offending: {offenders}")
        return proc
    try:
        get(f"/new_puzzle?{payload}", timeout=90)
    except Exception as exc:
        print(f"    load failed: {exc}")
    return proc


def private_deck(player: dict, name: str | None = None) -> list:
    """The hero's private deck, wherever this tree keeps it.

    There are two homes for one concept. `player.additional_deck` is the engine's
    single slot; `player.special_decks` is a name -> deck mapping, which is what a
    hero with *two* private decks needs (Hercules has a Labor deck and a Gift
    deck, and the single slot cannot hold both). Daredevil's Sense deck lives in
    the mapping too.

    Resolving both here keeps a case portable, and keeps the failure honest: a
    case that reads the wrong slot reports an empty deck, which looks exactly
    like the ability never firing.

    Pass `name` for a hero with several; otherwise a lone entry is unambiguous
    and is used. With more than one and no name, return nothing rather than
    guess -- `special_deck` is the key for that.
    """
    if name is not None:
        return (player.get("special_decks") or {}).get(name) or []
    single = player.get("additional_deck") or []
    if single:
        return single
    special = player.get("special_decks") or {}
    if len(special) == 1:
        return next(iter(special.values())) or []
    return []


def read_world() -> dict:
    return json.loads(get("/get_world?p=0"))


def names(items) -> list:
    return [x.get("name") for x in (items or []) if isinstance(x, dict)]


def evaluate(expect: dict, world: dict, driver_out: str) -> list[str]:
    """Return a list of human-readable failures; empty means the case passed."""
    fails: list[str] = []
    player = (world.get("players") or [{}])[0]
    hero_area = player.get("area_hero") or []
    faceup = [x for x in hero_area if x.get("is_face_up")]
    hero = next((x for x in faceup
                 if (x.get("info") or {}).get("health") is not None), None)
    villain_area = world.get("area_villain") or []

    def check(key, actual, want):
        if actual != want:
            fails.append(f"{key}: expected {want!r}, got {actual!r}")

    for key, want in expect.items():
        if key == "hero_hp":
            check(key, (hero or {}).get("info", {}).get("health"), want)
        elif key == "hero_attack":
            check(key, (hero or {}).get("info", {}).get("attack"), want)
        elif key == "main_scheme_threat":
            schemes = world.get("area_schemes_main") or []
            actual = (schemes[0].get("info", {}).get("k_threat")
                      if schemes else None)
            check(key, actual, want)
        elif key == "tucked":
            # Tucked cards render as face-down entries bound to their host card.
            hosts = {x.get("id") for x in faceup}
            actual = len([x for x in hero_area
                          if not x.get("is_face_up")
                          and x.get("bind_object_id") in hosts])
            check(key, actual, want)
        elif key == "enemy_hp":
            for enemy_name, hp in want.items():
                got = next(((x.get("info") or {}).get("health")
                            for x in villain_area
                            + (player.get("engaged_enemies") or [])
                            if x.get("name") == enemy_name), None)
                check(f"{enemy_name} hp", got, hp)
        elif key == "villain_area_has":
            for n in want:
                if n not in names(villain_area):
                    fails.append(f"villain area missing {n!r}: {names(villain_area)}")
        elif key == "villain_area_lacks":
            for n in want:
                if n in names(villain_area):
                    fails.append(f"villain area unexpectedly has {n!r}")
        elif key == "engaged_has":
            got = names(player.get("engaged_enemies"))
            for n in want:
                if n not in got:
                    fails.append(f"not engaged with {n!r}: {got}")
        elif key == "allies":
            check(key, names(player.get("allies")), want)
        elif key == "player_discard_has":
            got = names(player.get("player_discard_pile"))
            for n in want:
                if n not in got:
                    fails.append(f"discard missing {n!r}: {got}")
        elif key == "dealt_encounter_cards_min":
            got = len(player.get("dealt_encounter_cards") or [])
            if got < want:
                fails.append(f"dealt_encounter_cards: expected >={want}, got {got}")
        elif key == "attack_prompts":
            got = len(re.findall(r"is being attacked by", driver_out))
            check(key, got, want)
        elif key == "additional_deck":
            # A hero's private deck: Doctor Strange's Invocation deck, Daredevil's
            # Sense deck, either of Hercules' two. Ordered bottom -> top, matching
            # Deck2.Get(), so the last entry is the top card. Assert the whole list
            # rather than a size: a size alone cannot tell "returned to the bottom"
            # from "returned to the top", which is the entire mechanic on 60001b.
            check(key, names(private_deck(player)), want)
        elif key == "special_deck":
            # Explicit form for a hero with more than one private deck, where
            # `additional_deck` would be ambiguous: {"hercules_labor": [...]}.
            for deck_name, expected in want.items():
                got = (player.get("special_decks") or {}).get(deck_name)
                if got is None:
                    fails.append(f"special_deck {deck_name!r} does not exist: "
                                 f"{sorted((player.get('special_decks') or {}))}")
                else:
                    check(f"special_deck[{deck_name}]", names(got), expected)
        elif key == "additional_deck_top_face_up":
            deck = private_deck(player)
            check(key, bool(deck and deck[-1].get("is_face_up")), want)
        elif key == "additional_discard":
            check(key, names(player.get("additional_discard_pile")), want)
        elif key == "player_discard":
            # Exact contents, unlike player_discard_has. Needed to prove a card did
            # NOT fall through to the normal discard pile.
            check(key, names(player.get("player_discard_pile")), want)
        elif key == "reaper_attackable_with_empty_hand":
            # 58027: the Attack option should not offer Grim Reaper when the
            # discard cost cannot be paid.
            reaper = next((x for x in (player.get("engaged_enemies") or [])
                           if x.get("name") == "Grim Reaper"), None)
            attackable = bool(reaper) and re.search(
                r"'Attack'.*targets=\[[^\]]*\b%d\b" % reaper.get("id", -1),
                driver_out)
            check(key, bool(attackable), want)
        else:
            fails.append(f"unknown expectation key {key!r}")
    return fails


def run_case(path: pathlib.Path, verbose: bool) -> str:
    case = json.loads(path.read_text())
    expect = case.get("expect") or {}
    xfail = case.get("xfail")
    driver = case.get("driver") or ["--steps", "30", "--greedy"]
    log_path = pathlib.Path("/tmp") / f"suite_{path.stem}.log"

    proc = boot(case, log_path)
    if proc is None:
        return f"ERROR   {path.stem}: engine failed to start"

    try:
        # `driver` is either one flag list, or a list of lists run in order against
        # the same server. Phases exist because a single strategy cannot express
        # "play your cards, *then* attack": --greedy picks the last option every
        # prompt, so whether the basic attack lands before or after the plays is
        # unpinned, and an assertion resting on that is a coin flip, not a test.
        phases = driver if driver and isinstance(driver[0], list) else [driver]
        driver_out = ""
        for phase in phases:
            out = subprocess.run(
                [PY, str(ROOT / "tools" / "headless_client.py"), *phase],
                cwd=ROOT, capture_output=True, text=True, timeout=200)
            driver_out += out.stdout + out.stderr
        engine_errors = driver_out.count("!! ENGINE ERROR")
        try:
            world = read_world()
        except Exception as exc:
            return f"ERROR   {path.stem}: could not read world ({exc})"
        fails = evaluate(expect, world, driver_out)
        if engine_errors:
            fails.append(f"{engine_errors} engine error(s) in render frames")
        if (ROOT / "crash.json").exists() or (ROOT / "crash.log").exists():
            fails.append("crash artifact written")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    if xfail:
        if fails:
            return f"XFAIL   {path.stem}\n          known gap — {xfail}"
        return (f"XPASS   {path.stem}: expected to fail but passed — "
                f"the gap may be fixed; promote this case\n          {xfail}")
    if fails:
        detail = "\n".join(f"          {f}" for f in fails)
        if verbose:
            detail += "\n" + "\n".join(f"          | {l}"
                                       for l in driver_out.splitlines()[-15:])
        return f"FAIL    {path.stem}\n{detail}"
    return f"ok      {path.stem}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-k", "--filter", default="", help="only cases whose name contains this")
    ap.add_argument("-v", "--verbose", action="store_true", help="show driver tail on failure")
    args = ap.parse_args()

    cases = sorted(p for p in CASES_DIR.rglob("*.json") if args.filter in p.stem)
    if not cases:
        print(f"no cases matching {args.filter!r} in {CASES_DIR}")
        return 1

    print(f"running {len(cases)} case(s) from {CASES_DIR.relative_to(ROOT)}\n")
    results = []
    for path in cases:
        line = run_case(path, args.verbose)
        print(line, flush=True)
        results.append(line)

    bad = [r for r in results if r.startswith(("FAIL", "ERROR", "XPASS"))]
    xfail = [r for r in results if r.startswith("XFAIL")]
    ok = [r for r in results if r.startswith("ok")]
    print(f"\n{len(ok)} passed, {len(xfail)} xfail, {len(bad)} failed")
    free_port()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
