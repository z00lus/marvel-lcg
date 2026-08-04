# AGENTS.md

This file applies to the entire repository. It is guidance for coding agents working on this fork of Marvel LCG.

## Project overview

Marvel LCG is a Python game engine with an aiohttp web server and a browser frontend written in HTML, CSS, and TypeScript.

The main layers are:

- `core/`: shared types, metaclasses, debugging, math, and low-level utilities.
- `engine/`: configuration, lifecycle, logging, file/cache handling, networking, devices, jobs, and tasks.
- `game/`: runtime game state, cards, effects, messages, selectors, players, rules, rendering descriptors, scenes, and replays.
- `cards/`: card database loading and executable Python scripts grouped by expansion.
- `data/`: card metadata, set metadata, scenarios, encounter sets, challenges, and nemesis data.
- `public/`: browser UI. TypeScript sources live under `public/js/`; emitted JavaScript is generated and ignored by Git.
- `unit_test/` and `game/test/`: replay-driven tests. The full replay corpus is not included in a clean checkout.
- `assets/`: downloaded card images, local textures, sounds, and cache files. The whole directory is ignored by Git.

The process entry point is `main.py`: `Engine.Initialize()` -> `Engine.EngineRun()` -> `Engine.Shutdown()`.

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

When changing only documentation or configuration, a full game run is usually unnecessary; validate syntax and the exact affected path instead.

## Python conventions and architecture

- Existing modules commonly use `from core import *`, quoted forward-reference annotations, `@override`, and `@final`. Match the local convention rather than rewriting imports wholesale.
- `ConfigVariables` merges command-line arguments, `launch.json`, and defaults in that priority order. Path variable names must use the expected suffixes such as `_file`, `_files`, `_folder`, and `_folders`.
- Preserve lifecycle cleanup. New managers, aiohttp runners, jobs, and tasks must participate in shutdown so Ctrl+C and systemd `SIGINT` do not leave pending tasks.
- Game behavior is event/message driven. Prefer existing `AbilityFactory`, `Message`, `Faces`, `Effects`, `Worlds`, `Players`, `Search`, and selector operations over direct state mutation; these helpers preserve trigger windows, logging, replay, and rendering behavior.
- Preserve replay determinism. Use the project's seeded random abstractions for gameplay decisions; do not introduce unseeded Python randomness into game resolution.
- Rendering is a Python/TypeScript contract. When changing a descriptor in `game/render/descriptor/` or `game/render/to_descriptor.py`, update the corresponding TypeScript descriptor and all consumers in the same change.
- Web routes live in the mixins under `engine/device/web/server/`. Use the appropriate authenticated route registration helper. Keep specific routes registered before the final catch-all static/image route.
- Treat values received through HTTP, replay files, and custom card scripts as untrusted input. Preserve authentication and version checks unless a route has a documented reason to bypass them.

## Card and data changes

- Card scripts live under `cards/pack/<expansion>/...` and their filenames match `card_id` values in `data/cards.json`.
- Pack-level `__init__.py` files normally contain `from cards.pack import *`; card scripts normally import from their package with `from . import *`.
- A scripted card generally exposes `GetAbilities() -> Sequence['Ability']`. Follow nearby cards of the same type and the patterns in `docs/card_scripting_guide.md`.
- Card metadata and executable behavior are separate. Adding a card may require both a `data/cards.json` entry and a matching Python script, plus set/scenario/deck data where appropriate.
- `data/cards.json` and `data/sets_info.json` contain checksums. Preserve their checksum semantics; prefer the existing editor/`Json.Save(..., ignore_check_sum=False)` path when regenerating these files. Do not silently leave a stale checksum.
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
- Runtime state such as `save_*.json`, `statistics.json`, `crash.json`, `crash.log`, and most deck JSON files is ignored by Git. Preserve these files during diagnosis unless the user explicitly asks to remove them.
- Do not publish bundled card art or other ignored assets in the public fork.

## Deployment

- `marvel-lcg.service` assumes `User=marvel-lcg`, `Group=marvel-lcg`, and `WorkingDirectory=/opt/marvel-lcg`.
- The service needs write access inside `/opt/marvel-lcg` for cache, statistics, saves, and crash output.
- Follow `INSTALL-SERVER.md` for user creation, virtualenv preparation, unit installation, logs, and updates.
- Validate deployment changes against both direct `./run.sh` use and the systemd execution path; they intentionally have different bootstrap behavior.
