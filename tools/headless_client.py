#!/usr/bin/env python3
"""A minimal headless client, so a game can be driven without a browser.

The engine only builds the world once a client connects and syncs — `GameSetup`
blocks in `WaitConnect`.  That makes it impossible to verify a new pack from the
command line alone, so this speaks the same protocol the browser does:

    ws /ws?p=0                      connect, then send "Connected <url>"
    <- render frames as JSON        one per render
    GET client_updated?p&r&g        acknowledge a frame
    GET get_ask?p=0                 what input is wanted, if any
    POST post?p=0                   submit a choice (url-encoded body)

By default it answers every prompt with the first option, which is enough to walk
through setup and see whether a hero's cards behave.  Use --auto-first-n to stop
after N answers, or --dump-asks to print each prompt payload.

Usage:
  python3 tools/headless_client.py --steps 40 --dump-asks
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.parse

import aiohttp

BASE = "http://127.0.0.1:2345"


async def app_version_cookies(session: aiohttp.ClientSession) -> dict:
    """Read `app_version` off the server instead of hardcoding it.

    A stale value here is silent and misleading: every path answers with the
    version-mismatch interstitial, so `/ws` fails its handshake with
    "Invalid response status" and nothing mentions the version. `/get_version`
    is exempt from the check (`need_check_version=False`) so it can be read
    first.
    """
    async with session.get(f"{BASE}/get_version") as response:
        version = (await response.text()).strip()
    if not version:
        raise RuntimeError("/get_version returned nothing")
    return {"app_version": version}


def pick_payment(opt: dict, target: int | None, overpay: int,
                 color: str | None) -> list[str]:
    """Choose which resources to spend, so overpay effects can be exercised.

    An option carries `target_payment: {target_id: {cost, payment, rule}}`, where
    `payment` is a list of single-entry `{effect_id: res_letter}` dicts — one per
    card in hand that could pay.  Cards that scale with overpayment (Wonder Man's
    energy events, Wasp) read the amount paid above cost off the effect context,
    so the only way to test them is to name more pay effects than the cost needs.
    """
    table = opt.get("target_payment") or {}
    if not table:
        return []
    # Keyed by target id, but a single "0" entry stands for "any target".
    entry = table.get(str(target)) or table.get("0") or next(iter(table.values()))
    try:
        cost = int(entry.get("cost") or 0)
    except (TypeError, ValueError):
        cost = 0

    ids: list[str] = []
    for pay in entry.get("payment") or []:
        for effect_id, res in pay.items():
            if color and color.upper() not in str(res).upper():
                continue
            ids.append(str(effect_id))
    return ids[: cost + overpay]


async def run(steps: int, dump_asks: bool, answer: str | None, quiet: bool,
              passive: bool = False, greedy: bool = False,
              avoid: str | None = None, prefer: str | None = None,
              overpay: int | None = None, pay_color: str | None = None,
              strict: bool = False, decline: str | None = None) -> int:
    frames = 0
    answers = 0
    errors = 0
    async with aiohttp.ClientSession() as session:
        session.cookie_jar.update_cookies(await app_version_cookies(session))
        async with session.ws_connect(f"{BASE}/ws?p=0") as ws:
            await ws.send_str(f"Connected {BASE}/")
            print("connected")

            while frames < steps:
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=20)
                except asyncio.TimeoutError:
                    print("no frame for 20s — stopping")
                    break
                if msg.type is not aiohttp.WSMsgType.TEXT:
                    print(f"ws closed: {msg.type}")
                    break

                # The engine does not log ability failures to stdout, and it only
                # writes crash.json for exceptions that reach Message.Send. A
                # handler that fails another way surfaces solely as text pushed
                # into a render frame by World.render.ErrorOccurred, so scanning
                # the raw frame is the only reliable error signal a driver has.
                if "Error occurred" in msg.data:
                    errors += 1
                    snippet = msg.data[max(0, msg.data.find("Error occurred")):][:300]
                    print(f"!! ENGINE ERROR in frame {frames + 1}: {snippet}")

                frame = json.loads(msg.data)
                frames += 1
                render_id = frame.get("render_id", 0)
                game_id = frame.get("game_id", 0)
                asking = frame.get("ask_players") or []
                if not quiet:
                    print(f"frame {frames}: render_id={render_id} game_id={game_id} asking={asking}")

                await session.get(
                    f"{BASE}/client_updated?p=0&r={render_id}&g={game_id}"
                )

                async with session.get(f"{BASE}/get_ask?p=0") as resp:
                    text = await resp.text()
                ask = json.loads(text) if text.strip() else {}
                # The payload nests the option list as a JSON *string*.
                options = json.loads(ask.get("options_json") or "[]")
                if not options:
                    continue

                if dump_asks:
                    print(f"  prompt: {(ask.get('prompt_text') or '')[:150]}")
                    for i, opt in enumerate(options[:12]):
                        print(f"    [{i}] id={opt.get('id')} {opt.get('name')!r} "
                              f"targets={opt.get('all_legal_targets')} "
                              f"range={opt.get('target_num_range')}")
                        if opt.get("target_payment"):
                            print(f"         pay={json.dumps(opt['target_payment'])}")

                if passive:
                    # Stay attached so renders flush, but never answer.  The game
                    # parks on the prompt, which keeps state still while cheat
                    # commands are sent over /debug (those call ExitWait, so they
                    # are processed even while input is pending).
                    continue

                # Steering: drop options whose name matches --avoid (e.g. Change_Form,
                # which otherwise flips the hero back and undoes the setup), and
                # jump straight to one matching --prefer.  Both take a comma-separated
                # list.  --prefer falls back to the whole pool when nothing matches, so
                # for a measurement run also --avoid the actions that would perturb it
                # (a bare "--prefer Play" happily takes a basic attack once the hand is
                # empty, and the extra damage looks like the card under test).
                pool = options

                def matches(opt: dict, spec: str) -> bool:
                    name = str(opt.get("name", "")).lower()
                    return any(part.strip().lower() in name
                               for part in spec.split(",") if part.strip())

                # Declining is not "pick a different option" — an optional prompt has
                # no decline entry in its option list. Posting id 0 is what the engine
                # reads as no/cancel (`input_effect_id == 0` breaks out of the ask loop,
                # engine/controller/controller.py:274). --avoid cannot express this: it
                # filters the pool, so a single-option prompt either falls back to that
                # option or, under --strict, parks forever and the attack never
                # resolves. Needed for any measurement of an attack, because a basic
                # defense subtracts DEF and can clamp the damage to 0, hiding exactly
                # the modifier under test.
                #
                # Only decline where the engine allows it: `show_cancel` is false for a
                # forced prompt, and posting 0 there trips an assert
                # (controller.py:275-276). Fall through to normal selection instead.
                if decline and any(matches(o, decline) for o in options) \
                        and ask.get("show_cancel"):
                    body = json.dumps({"id": 0, "targets": [], "resources": []})
                    await session.post(
                        f"{BASE}/post?p=0",
                        data=body,
                        headers={"Content-type": "application/x-www-form-urlencoded"},
                    )
                    answers += 1
                    if not quiet:
                        print(f"  -> declined {body}")
                    continue

                if avoid:
                    filtered = [o for o in pool if not matches(o, avoid)]
                    if not filtered and strict:
                        continue  # park rather than take an option we ruled out
                    pool = filtered or pool
                if prefer:
                    wanted = [o for o in pool if matches(o, prefer)]
                    if not wanted and strict:
                        continue
                    pool = wanted or pool

                # Default: first option with the fewest legal targets, which is the
                # "decline / keep / do nothing" branch for most prompts.  Greedy
                # instead takes the last option and the most targets, so optional
                # responses actually fire — needed to exercise triggered abilities.
                opt = pool[-1] if greedy else pool[0]
                rng = opt.get("target_num_range") or [0, 0]
                legal = opt.get("all_legal_targets") or []
                targets = legal[: rng[1]] if greedy else legal[: rng[0]]
                # Always name the pay effects. There is no "let the engine choose"
                # mode: posting `resources: []` for a card that costs anything means
                # nothing is spent, `CheckBeforeActive` fails its `check_pay`
                # (game/effect/effect_checker.py:187-213) and `ResolveEffect`
                # discards the card from the processing area
                # (game/player/action/player_action.py:417-419) — silently, with no
                # engine error and no crash file. Every non-zero-cost card was
                # unplayable through this client until this line paid for it; it
                # looked like "upgrades cannot attach" only because an upgrade that
                # fails to play lands somewhere visible.
                # `--overpay N` still adds N above the printed cost.
                resources = pick_payment(opt, targets[0] if targets else None,
                                         overpay or 0, pay_color)
                body = answer if answer is not None else json.dumps(
                    {"id": opt.get("id"), "targets": targets, "resources": resources}
                )
                await session.post(
                    f"{BASE}/post?p=0",
                    data=body,
                    headers={"Content-type": "application/x-www-form-urlencoded"},
                )
                answers += 1
                if not quiet:
                    print(f"  -> posted {body}")

    print(f"done: {frames} frames, {answers} answers, {errors} engine errors")
    return 1 if errors else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=40, help="max frames to process")
    ap.add_argument("--dump-asks", action="store_true", help="print each prompt and its options")
    ap.add_argument("--answer", default=None, help="value to post for every prompt (default '0')")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--passive", action="store_true",
                    help="ack frames but never answer, so cheat commands can drive the game")
    ap.add_argument("--greedy", action="store_true",
                    help="take the last option and the most targets, so optional responses fire")
    ap.add_argument("--avoid", default=None, help="skip options whose name contains this")
    ap.add_argument("--prefer", default=None, help="prefer options whose name contains this")
    ap.add_argument("--overpay", type=int, default=None,
                    help="pay this many resources above the printed cost "
                         "(0 = pay exactly cost; omit = let the engine choose)")
    ap.add_argument("--pay-color", default=None,
                    help="only spend resources of this letter (R/Y/G/B)")
    ap.add_argument("--strict", action="store_true",
                    help="never substitute an unwanted option: if --avoid/--prefer "
                         "leave nothing, park on the prompt instead of answering. "
                         "Use for measurement runs so no stray action skews the result.")
    ap.add_argument("--decline", default=None,
                    help="say NO to any prompt offering an option whose name contains "
                         "this (comma-separated), by posting id 0. Unlike --avoid, "
                         "which only filters the option list, this refuses the prompt "
                         "outright — the way to skip a defense so an attack lands for "
                         "full damage. Ignored on forced prompts.")
    args = ap.parse_args()
    return asyncio.run(run(args.steps, args.dump_asks, args.answer, args.quiet,
                           args.passive, args.greedy, args.avoid, args.prefer,
                           args.overpay, args.pay_color, args.strict, args.decline))


if __name__ == "__main__":
    sys.exit(main())
