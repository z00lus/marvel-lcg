---
name: marvel-lcg-player
description: "Play, test, or diagnose Marvel Champions Digital: Ronin Edition solo games through the local marvel_lcg MCP server. Use when asked to play a full game, test a hero/deck/scenario, reproduce a gameplay problem, inspect a running headless game, or save and analyze the resulting replay."
---

# Marvel LCG Player

Use the `marvel_lcg` MCP tools. Do not open a browser, inspect the DOM, connect a
WebSocket, or drive the visible UI for a task this skill covers.

## Start or resume

1. Call `catalog` unless the requested hero and scenario IDs are already known.
2. Call `start_game` for a new game or `continue_game` for the server's active
   session. Starting a game intentionally replaces the previous active session.
3. `start_game` and `continue_game` normally return the first stable
   `awaiting_input` or `game_over` snapshot directly. If the returned status is
   transiently `starting` or `running`, call `observe` with `wait_ms: 2000`.

## Play the game

At every prompt:

1. Read `recent_log`, the board zones, and every current option before deciding.
2. Choose only an `effect_id` returned by that prompt.
3. Choose target IDs only from that option's `legal_targets`, respecting
   `target_range` and any selection rule.
4. For a paid action, use resource-effect IDs from the payment entry for the
   selected target (`"0"` is the target-independent entry). Select enough valid
   resources to meet the cost and make deliberate choices about which hand
   cards to spend. Never assume the engine will auto-pay an empty resource list.
5. Call `act` with the exact prompt `revision`. Use `skip` only when
   `can_skip` is true and declining is strategically intended. Both tools wait
   briefly for rules resolution and normally return the next stable decision,
   so use that returned snapshot immediately.
6. Call `observe` only when `act` or `skip` returns `starting` or `running`.
   Pass the previous revision and step with `wait_ms: 2000`. Do not add a fixed
   30-second host-side wait around MCP calls; if a persistent stdio fallback is
   unavoidable, its output-yield interval should be at most 250-1000 ms.

Play strategically rather than selecting the first legal option. Track hero HP,
main-scheme threat, engaged minions, statuses, ready/exhausted cards, remaining
deck, hand economy, and the villain's stage. In solo games, avoid ending a turn
with an immediate unresolved loss condition merely to progress quickly.

Treat Rules Reference 1.8 and the engine's returned legal choices as the runtime
contract. Do not use debug/cheat commands during a genuine playtest. For a bug
reproduction, preserve the exact sequence and distinguish a rules error from a
poor strategic outcome.

Games started or continued through this MCP are deliberately excluded from the
user's game history, aggregate statistics, ratings, and achievement progress.
The replay saved at the end is the only permanent game record created for an
autonomous playtest.

## Finish and report

When `game_over` is returned:

1. Call `save_replay` before disconnecting, unless the user explicitly said not
   to save it.
2. Record win/loss, rounds, decisive cards and effects, economy, threat control,
   damage plan, and any suspicious behavior or engine errors from the log.
3. Call `disconnect` after the replay is safely stored.

If an engine error appears or no legal action can advance a non-final game, save
the replay/current evidence, stop making speculative inputs, and report the
prompt, step, option, targets, and resources that caused it.

Read [references/mcp-contract.md](references/mcp-contract.md) when a tool field,
payment entry, or state zone is unclear.
