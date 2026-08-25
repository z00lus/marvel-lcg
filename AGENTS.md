# AGENTS.md

This file applies to the entire repository. It is guidance for coding agents working on **Marvel Champions Digital: Ronin Edition**.

## Project overview

Marvel Champions Digital: Ronin Edition is a Python game engine with an aiohttp web server and a browser frontend written in HTML, CSS, and TypeScript. The current development identity is **Version 0.6.1 — “Echo”**.

The main layers are:

- `core/`: shared types, metaclasses, debugging, math, and low-level utilities.
- `engine/`: configuration, lifecycle, logging, file/cache handling, networking, devices, jobs, tasks, and print-ready proxy generation.
- `game/`: runtime game state, cards, effects, messages, selectors, players, rules, rendering descriptors, scenes, and replays.
- `cards/`: card database loading and executable Python scripts grouped by expansion.
- `data/`: card metadata, set metadata, scenarios, encounter sets, challenges, and nemesis data.
- `public/`: browser UI. TypeScript sources live under `public/js/`; emitted JavaScript is generated and ignored by Git.
- `unit_test/` and `game/test/`: replay-driven tests. The full replay corpus is not included in a clean checkout.
- `assets/`: downloaded card images, local textures, sounds, and cache files. The whole directory is ignored by Git.

The process entry point is `main.py`: `Engine.Initialize()` -> `Engine.EngineRun()` -> `Engine.Shutdown()`.

### Fork priorities

- The primary supported use case for this fork is solo play with one hero, with the Python server running on Linux and the browser connecting over the local network.
- Prioritize solo rules correctness, easy starter-deck selection, reliable saves/replays, and modest resource use on low-power servers.
- PvP and broad four-player improvements are out of scope unless the user explicitly requests them. Do not start an engine rewrite solely to address upstream multiplayer limitations.
- Preserve existing multiplayer behavior when making shared engine changes where practical, but do not let speculative multiplayer work expand a solo-focused task.
- Rules Reference 1.8 is the only supported runtime rules model in this fork.
  Do not add legacy v1.6/v1.7
  execution branches or compatibility flags. New games must record `v18_all`;
  older replay/save files are intentionally unsupported and must fail early
  with a clear compatibility error.

Read these documents before making broad changes:

- `docs/engine_architecture.md`
- `docs/card_scripting_guide.md`
- `docs/debug_guide.md`
- `INSTALL-SERVER.md` for the `/opt/marvel-lcg` systemd deployment

## Working rules

- Inspect `git status` before editing. Preserve unrelated and user-owned changes.
- Keep changes scoped. This codebase has many implicit contracts and extensive wildcard re-exports; avoid opportunistic refactors.
- Follow the style in the surrounding file. There is no repository-wide formatter or linter configuration.
- Do not commit or push unless the user explicitly requests it.
- Do not add `assets/`, `.venv/`, generated JavaScript, saves, statistics, crash files, or downloaded cache files to Git.
- Do not run release/version scripts casually. `build_marvel.py` modifies `build.py`, stages it, and creates a Git commit.
- Do not run unrestricted unittest discovery. `unit_test/test_task.py` contains maintenance tasks that can increment the version, create a commit, or produce archives.
- Card scripts are executable Python. Do not install or execute untrusted third-party card scripts.

## Setup and run

Python 3.10 or newer is required.

Preferred local startup:

```bash
./run.sh
```

`run.sh` creates `.venv`, installs `requirements.txt` when needed, compiles stale TypeScript, checks port `2345`, and runs `main.py`.

Important runtime facts:

- `launch.json` is the main configuration file. Command-line values override it.
- `server_addresses` currently binds the game server to `0.0.0.0:2345` for LAN access.
- The configured password is empty. Do not expose this server directly to the public Internet.
- Only one server can bind port `2345`. A second process fails during initialization.
- `Build.release` is currently forced to `True` in `build.py`; many initialization/runtime exceptions are logged rather than propagated normally. Inspect console output and `crash.log` when diagnosing failures.
- The systemd unit starts `/opt/marvel-lcg/.venv/bin/python` directly. Installation must prepare dependencies and compiled frontend files before starting the service.

## Validation

Run checks proportional to the files changed.

Python syntax/import-oriented check:

```bash
.venv/bin/python -m compileall -q core engine game cards unit_test
```

Frontend type-check and build:

```bash
npm exec --yes --package=typescript -- tsc --project public/js/tsconfig.json
```

The TypeScript command emits `.js` and `.js.map` files next to sources. These are runtime artifacts and are intentionally ignored by Git.

For a server/UI smoke test, run `./run.sh` only when port `2345` is available, open the reported URL, and stop it with Ctrl+C. Starting the server may download missing numeric card images into `assets/cache/`.

Replay tests require local replay data and, in the current test harness, a `launch-debug.json` configuration that is not part of a clean checkout. A targeted command, when those files are available, is:

```bash
.venv/bin/python -m unittest unit_test.test_all.TestMain.test_min
```

Do not claim the replay suite passed when its external fixtures are unavailable. Do not substitute `python -m unittest` without a specific test target because of the maintenance tasks in `unit_test/test_task.py`.

Focused tests for the newer persistent-data, proxy, and hero integrations can
be run without unrestricted discovery:

```bash
.venv/bin/python -m unittest \
  unit_test.test_game_history \
  unit_test.test_proxy_pdf \
  unit_test.test_jessica_jones_integration \
  unit_test.test_real_card_activation_regressions
```

For new or changed card scripts, explicitly import each affected module and exercise `GetAbilities()` or create its `CardFace` in an isolated smoke check. `CardsDB` tries several module paths and silently ignores import exceptions, so a successful database initialization or server start does not prove that a card script loaded. When diagnosing these failures, temporarily use `Build.release = False` only inside the isolated validation process so assertions and exceptions remain visible; do not commit that setting.

Treat structural and rules validation as separate stages. Compilation, checksum validation, module import, and card creation prove that the integration is structurally loadable. They do not prove timing, targeting, setup, resource, or discard behavior. Validate semantic card changes with a focused game/replay and compare the observed sequence with the card text and the local rules reference when available.

When changing only documentation or configuration, a full game run is usually unnecessary; validate syntax and the exact affected path instead.

## Python conventions and architecture

- Existing modules commonly use `from core import *`, quoted forward-reference annotations, `@override`, and `@final`. Match the local convention rather than rewriting imports wholesale.
- `ConfigVariables` merges command-line arguments, `launch.json`, and defaults in that priority order. Path variable names must use the expected suffixes such as `_file`, `_files`, `_folder`, and `_folders`.
- Preserve lifecycle cleanup. New managers, aiohttp runners, jobs, and tasks must participate in shutdown so Ctrl+C and systemd `SIGINT` do not leave pending tasks.
- Game behavior is event/message driven. Prefer existing `AbilityFactory`, `Message`, `Faces`, `Effects`, `Worlds`, `Players`, `Search`, and selector operations over direct state mutation; these helpers preserve trigger windows, logging, replay, and rendering behavior.
- Preserve determinism for v1.8 replays. Use the project's seeded random abstractions for gameplay decisions; do not introduce unseeded Python randomness into game resolution.
- Replay and undo reconstruct state by deterministically re-executing recorded choices and operations rather than restoring arbitrary Python snapshots. Keep gameplay state inside the modeled world/messages, avoid dependence on wall-clock time or external mutable state, and do not hide required replay state only inside transient closures.
- Rendering is a Python/TypeScript contract. When changing a descriptor in `game/render/descriptor/` or `game/render/to_descriptor.py`, update the corresponding TypeScript descriptor and all consumers in the same change.
- Web routes live in the mixins under `engine/device/web/server/`. Use the appropriate authenticated route registration helper. Keep specific routes registered before the final catch-all static/image route.
- Treat values received through HTTP, replay files, and custom card scripts as untrusted input. Preserve authentication and version checks unless a route has a documented reason to bypass them.

## Card and data changes

- Card scripts live under `cards/pack/<expansion>/...` and their filenames match `card_id` values in `data/cards.json`.
- Pack-level `__init__.py` files normally contain `from cards.pack import *`; card scripts normally import from their package with `from . import *`.
- A scripted card generally exposes `GetAbilities() -> Sequence['Ability']`. Follow nearby cards of the same type and the patterns in `docs/card_scripting_guide.md`.
- Card metadata and executable behavior are separate. Adding a card may require both a `data/cards.json` entry and a matching Python script, plus set/scenario/deck data where appropriate.
- Starter decks under `deck/starter/` separate the identity-specific `hero_deck` from the aspect/basic `player_deck`. A legal constructed player deck has 40-50 cards total and normally includes the hero's 15-card identity set. Keep obligations and nemesis cards outside that count.
- The player setup path currently does not consume a starter deck's `set_aside` list: `SelectIdentity()` generates the identity, obligations, nemesis set, `hero_deck`, and `player_deck`, while its generic set-aside generation is disabled. Cards that must start set aside or enter play during setup therefore need explicit supported setup behavior, such as an existing setup ability/operation; do not assume the JSON field alone is sufficient.
- For an exact reprint, `full_link` can reuse an earlier card's metadata, scripted abilities, and cached image link. The referenced card must already have been loaded. Do not add a duplicate script or image unless the reprint actually differs.
- `data/cards.json` and `data/sets_info.json` contain checksums. Preserve their checksum semantics; prefer the existing editor/`Json.Save(..., ignore_check_sum=False)` path when regenerating these files. Do not silently leave a stale checksum.
- `data/sets_info.json` is also the physical-product catalog. A product-level
  `"out_of_print": true` flag is the single source of truth for Proxy menu
  eligibility. Keep the browser filter and server-side validation derived from
  this catalog; do not maintain a second hard-coded allowlist. Synced
  MarvelCDB decks inherit eligibility from their identity's catalogued Hero
  Pack, while individual cards are not checked separately.
- Reuse existing operations and selectors so status, steady/stalwart, forced timing, ownership, visibility, and multiplayer behavior remain consistent.
- Test card-rule changes with a focused replay or a minimal reproducible game state when fixtures are available. A successful import or server start does not validate card timing rules.

## Frontend changes

- Edit `.ts` files, not ignored emitted `.js` files. Always compile TypeScript after changing frontend logic.
- `public/scene.html`, `public/deck.html`, and several other pages contain substantial inline JavaScript; changes there do not pass through the TypeScript compiler, so review and smoke-test them directly.
- Preserve UTF-8 in HTML and source files. Include `<meta charset="UTF-8">` on standalone pages that render localized text.
- Keyboard handlers must call the same guarded button methods as pointer controls. Do not bypass disabled-state, selection-step, pause, or lost-connection checks.
- Browser caching is intentionally long-lived in release mode. When validating updated frontend or textures, restart the server if its in-memory cache is involved and hard-refresh the browser. Avoid globally setting `cache_max_age` to zero for the low-power server deployment without a specific reason.

## Images, textures, and runtime files

- Image lookup searches configured image folders, `assets/textures/`, and `assets/cache/`.
- Numeric card IDs can be downloaded from configured image servers and cached automatically.
- Textual resources are local assets. Important names include `tough`, `stunned`, `confused`, `player`, `encounter`, `villain`, `mask.svg`, and set covers under `assets/textures/sets/`.
- Missing images are replaced with generated placeholders and cached in process memory. After adding a previously missing texture, restart the server and hard-refresh the browser.
- Implemented cards with known metadata but unavailable art are rendered as
  readable text-only cards by `engine/lib/image_creator.py`. Preserve their
  title, type, cost, resources, traits, stats, and rules text when extending
  the fallback renderer.
- Runtime state such as `save_*.json`, `statistics.json`, `crash.json`, `crash.log`, and most deck JSON files is ignored by Git. Preserve these files during diagnosis unless the user explicitly asks to remove them.
- Proxy PDFs are generated under the ignored `proxy-output/` directory. Both
  the `/proxy` UI and `/proxy/generate` endpoint must enforce product-level
  out-of-print eligibility; client filtering alone is not sufficient.
- Do not publish bundled card art or other ignored assets in the public fork.

## Persistent game history

- `statistics.sqlite3` stores digital and physical game history, collection
  ownership, achievements, and optional hero/scenario ratings. Treat schema
  changes as migrations in `game/statistics/game_history.py` and preserve
  existing rows.
- End-game ratings are optional integers from 1 through 5 and may be updated
  independently. Exit/undo states are not completed games and must not create
  rating targets.

## Deployment

- `marvel-lcg.service` assumes `User=marvel-lcg`, `Group=marvel-lcg`, and `WorkingDirectory=/opt/marvel-lcg`.
- The service needs write access inside `/opt/marvel-lcg` for cache, statistics, saves, and crash output.
- Follow `INSTALL-SERVER.md` for user creation, virtualenv preparation, unit installation, logs, and updates.
- Validate deployment changes against both direct `./run.sh` use and the systemd execution path; they intentionally have different bootstrap behavior.
