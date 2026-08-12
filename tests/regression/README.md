# Puzzle regression cases

Each case boots a real engine, loads a puzzle, drives it through the websocket
like a player, and asserts on the **resulting board**.

That last part is the whole point. `AGENTS.md` already says it:

> Treat structural and rules validation as separate stages. Compilation,
> checksum validation, module import, and card creation prove that the
> integration is structurally loadable. They do not prove timing, targeting,
> setup, resource, or discard behavior.

and:

> Test card-rule changes with a focused replay or a minimal reproducible game
> state **when fixtures are available**.

These are those fixtures. A case is self-contained, so it needs no replay corpus
and no `launch-debug.json`.

## Running

```bash
python3 tools/puzzle_suite.py                # every case
python3 tools/puzzle_suite.py -k overpay     # only cases whose name contains this
python3 tools/puzzle_suite.py -v             # show driver frames on failure
```

Port `2345` must be free. Each case boots and tears down its own engine, so a
full run takes roughly a minute per case — this is a pre-release gate, not a
per-commit one. `tools/run_puzzle_case.sh` runs a single ad-hoc puzzle and prints
the board, which is the faster loop while writing one.

## Writing a case

A case is an ordinary puzzle file plus four optional keys. The engine ignores
them, because `Json.ConvertDictToDataclass` keeps only declared fields, so the
same file still loads as a normal puzzle.

| key | meaning |
|---|---|
| `driver` | arguments for `tools/headless_client.py` |
| `expect` | board assertions (see below) |
| `xfail` | a known gap — **failing is the pass**, and an XPASS means it got fixed |
| `note` | prose: what this pins and why |

`driver` may be a list of lists, and the phases run in order against the same
server. Use phases whenever the assertion depends on *ordering* — a single
`--greedy` pass cannot express "play your cards, **then** attack", and an
expectation resting on that is a coin flip rather than a test.

### Assertions

`expect` keys read the world the client sees: `hero_hp`, `enemy_hp`,
`main_scheme_threat`, `allies`, `engaged_has`, `player_discard`,
`player_discard_has`, `tucked`, `attack_prompts`, `additional_deck`,
`additional_deck_top_face_up`, `additional_discard`, `special_deck`,
`dealt_encounter_cards_min`.

## Things that will bite you

Each of these cost real debugging time.

**Assert on state, never on the absence of errors.** A handler given a
wrong-typed argument can fail with no exception, no `crash.json`, and no client
error. Board state is the only signal that catches it.

**Write assertions that cannot pass vacuously.** `tucked: 0` passes when nothing
was ever tucked. Assert a downstream value that requires the whole chain — a
final HP that is only reachable if every step happened.

**No value may contain a space.** `/new_puzzle` reads the query string raw and
never percent-decodes it, so one space anywhere silently breaks the load and
every assertion then fails against an empty board. Put prose in `note`, which is
stripped from the payload; `comment` reaches the engine and must stay a single
token. The runner checks this up front and names the offending key.

**Pin the driver.** `--avoid` / `--prefer` fall back to the full option list when
nothing matches, so an unpinned driver will happily take `Change_Form` once the
hand empties and flip the hero to alter-ego mid-measurement. Use `--strict`.

**Frame budget is part of the assertion.** Effects and their responses take
~10–20 frames to settle. Reading too early shows a half-resolved board that looks
exactly like a bug.

**Setup can cause the thing you are measuring.** Putting an enemy with
**Quickstrike** into play makes it attack immediately, which can make a
treachery's "he activates against you" look verified when the prompt came from
Quickstrike. Run a control with only the enemy in play and compare.

**Declining is `--decline`, not `--avoid`.** An optional prompt carries no "no"
entry, so filtering the pool cannot express refusal — under `--strict` the case
parks forever. The engine reads option id `0` as cancel.

**There is no "end turn" option.** The engine advances on its own once nothing is
left. To make a villain attack without a villain phase, use `Puzzle.Boost(cN)`
with a card that has no `Boost` key, or its icons change the ATK you are
measuring.

**Puzzle command arguments are object ids, not card ids.** Use the `cN` bindings.
A quoted `"60005"` is searched by *name* and, failing that, generates a brand new
card — so you silently get a sixth copy rather than the one already in the deck.
