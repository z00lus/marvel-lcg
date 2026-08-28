# Marvel Champions Digital: Ronin Edition Changelog

> Current release version: 0.6.1 — “Echo”

This document records the user-visible and development changes made in this
fork after it diverged from the original
[irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg) repository.

The comparison baseline is upstream commit
[`a77154a`](https://github.com/irefrixs/marvel-lcg/commit/a77154ab7e2f800a6ae82da6e67efd83dc3c8045)
(`master`, 2026-07-31). Version 0.6.0 is the first release carrying the
**Ronin Edition** name and the **Echo** codename.

## Version 0.6.1 — “Echo” (2026-08-28)

### Rules and cards

- Added **Stop the Presses!** in Standard and Expert modes, including seeded
  Daily Bugle Persona setup, stamina management, all four Persona abilities,
  and the required Tombstone and Tracksuit Mafia modular sets.
- Added **Protection Racket** in Standard and Expert modes with all five main
  scheme variants, deterministic solo setup, and the **Disasters** and
  **Tracksuit Mafia** modular sets.
- Added **Electro** as a selectable Fear No Evil underling for The Getaway,
  including all three villain stages, Electric Charge, and his complete
  encounter set in Standard and Expert games.
- Added **Purple Man** as a selectable Fear No Evil underling across all
  implemented mix-and-match scenarios, including INFLUENCED minions,
  command obligations, Converted allies, and his complete encounter set.
- Added **Hammerhead** as a selectable underling with all three villain
  stages, status-driven Headbutt behavior, Chameleon, and the full Maggia
  encounter set.
- Added **Typhoid Mary** as a selectable underling with her two-sided villain
  stages, Disturbed Psyche victory track, Mary Walker/Establish Trust cycle,
  and complete encounter set.
- Added the fixed **Kingpin** finale in Standard and Expert modes, including
  nemesis/UNDERLING setup, the two-stage main scheme, Public Support, and the
  complete Kingpin encounter set.
- Extended all five mix-and-match scenarios to offer every Fear No Evil
  underling, with the new choices and Kingpin marked clearly in Quick Game.
- Added **Art Museum Heist** in Standard and Expert modes, with deterministic
  ART attachment setup, all five underling choices, and
  the complete **The Owl** encounter set.
- Added **The Raft Breakout** in Standard and Expert modes, including Master
  Key setup, PRISONER minions, Imprisoned, all five underling choices, and the
  complete **Tombstone** encounter set.
- Added an explicit pre-attachment timing message for facedown boost cards so
  effects such as Public Support can replace the boost without consuming or
  misplacing the top encounter card.
- Corrected player-side-scheme rewards so cards such as Sidearm enter the
  proper player area instead of remaining detached on the table.
- Corrected Photographic Reflexes resolution and exclusive thwart-target
  restrictions such as Hope Summers being limited to Stryfe's Grasp.
- Added **Jessica Jones** with her identity cards, obligation, nemesis set,
  starter deck, and the additional cards required by her integration.
- Added readable text-only card images for implemented cards whose published
  artwork is unavailable, including title, type, cost, resources, traits,
  statistics, and rules text.
- Refreshed the availability of events tucked beneath Echo after the game
  state changes, so cards such as Army of One can be played at the correct
  time through Photographic Reflexes.
- Corrected reported Fear No Evil interactions: Contingency Planning now
  recognises printed attachment targets, Daredevil has his printed THW 2,
  Superior Taste follows the Rules Reference definition of “you”, and Raised
  by the Kingpin tracks the player who received the obligation.

### Interface

- Distinguished Retaliate damage from ordinary card activation in the game
  log.
- Removed the duplicate `was defeated` log entry emitted for defeated schemes.
- Added a prominent reminder that Ronin Edition is a testing and learning
  platform and is not a replacement for supporting the physical card game.
- Replaced the standalone Statistics page with a combined **Collection &
  Statistics** screen for tracking owned physical products, browsing game
  history, and reviewing achievements.
- Added a **Proxy** screen that produces print-ready A4 PDFs with cut lines for
  hero decks and scenarios belonging to catalogued out-of-print products.
  Eligibility is enforced on both the browser and server sides.
- Added a **Deck Viewer** for inspecting local and synced decks, showing each
  card's source product, and exporting a compact shareable PNG deck grid.
- Organised Quick Game heroes alphabetically within custom-deck and preconstructed
  groups, and grouped scenarios visually by expansion or scenario pack.
- Restyled the main menu and in-game controls, added a return-to-menu action to
  the game-over screen, and compacted the desktop table for clearer recording
  and play.
- Corrected fallback image caching so newly available card art can replace a
  previously generated placeholder after restart.

### Game history and achievements

- Added manual logging, editing, and deletion of physical solo games.
- Unified digital games, replay imports, and tabletop results in the same
  SQLite history, with source filters and shared hero, villain, and matchup
  win rates.
- Recalculate achievement progress after a physical result is corrected or
  removed, and order streak achievements by the actual played date.
- Added optional independent 1–5 star ratings for the hero and scenario after
  a completed game, with ratings stored alongside the game-history record.

### Automation and regression coverage

- Added an authenticated headless solo-play API, a local MCP bridge, and a
  repository-scoped Codex skill for running complete games without the browser
  UI. Agent-run games retain replays but are excluded from personal history,
  statistics, ratings, and achievements.
- Added a real-engine puzzle regression suite covering 20 compact rules and
  card-interaction cases, with isolated server lifecycle and cleanup.

## Version 0.6.0 — “Echo” (2026-08-11)

This is the first Ronin Edition release. The Rules Reference 1.8 work and the
fork changes described below are included in the `master` branch.

### Rules engine

- Made Rules Reference 1.8 the single runtime rules model and removed the old
  v1.6/v1.7/v1.8 behavior switches from game execution.
- Added explicit timing and priority handling for interrupts, responses,
  forced abilities, constant abilities, status cards, and simultaneous
  effects.
- Reworked ability initiation so legality, targets, costs, payment, and effect
  resolution occur in the required order and failed initiations cleanly roll
  back temporary state.
- Added deterministic surge queuing and corrected reveal, boost, quickstrike,
  overkill, indirect damage, and calculated-damage processing.
- Corrected referential targeting, target validation, card swaps, card
  ownership/control, uniqueness, permanent cards, restricted cards, counters,
  modifiers, and card-state transitions.
- Implemented cumulative rules needed from Rules Reference 1.7, including
  `otherwise`, `for each`, player choices, actions and activations, setup,
  attacks, villain-stage transitions, and the definition of “you”.
- Consolidated keyword and status handling into the normal event/message
  pipeline instead of retaining legacy ad-hoc execution paths.

### Cards and data

- Updated affected card scripts and metadata to follow the 1.8 timing,
  targeting, initiation, cost, status, and errata rules.
- Added focused corrections for cards from Black Panther, Core/Ultron,
  Falcon, Galaxy's Most Wanted, Iceman, Magneto, Ms. Marvel, and Psylocke.
- Regenerated the card database checksum after metadata corrections.

### Saves, replays, and UI

- New games always record the `v18_all` rules marker.
- Saves and replays created under older rules models are intentionally
  incompatible and now fail early with a clear compatibility error.
- Removed legacy rules toggles from new-game payloads and browser state.
- Updated setup and replay pages for the single-version rules model.

### Tests and documentation

- Added focused unit coverage for timing priority, defined terms, ability
  initiation, surge, reveal lifecycle, damage, overkill, targeting, swaps,
  setup, UI payloads, replay compatibility, card errata, and miscellaneous 1.8
  rules.
- Added cumulative 1.7 coverage for choices, ownership/control, referential
  abilities, uniqueness, actions/costs, counters/modifiers, attacks, villain
  transitions, setup, and “you”.
- Added a small self-contained v1.8 replay fixture so replay loading can be
  tested without the external upstream replay corpus.
- Added [`docs/rules_v18_compliance.md`](docs/rules_v18_compliance.md), updated
  the engine architecture and card scripting guides, and documented the
  v1.8-only policy in the repository guidance.
- Documented the use of a local, Git-ignored Rules Reference 1.8 copy under
  `rules/` for future rules audits and card validation.

## Fork changes since upstream

### Solo-first game setup

- Added a streamlined **Quick Game** screen focused on one hero versus one
  scenario.
- Added direct selection of prepared starter decks from `deck/starter/`, so a
  player does not need to upload a deck file before every game.
- Remembered the last selected hero and scenario in browser `localStorage` and
  restored them after a reload.
- Disabled **Play** until both required selections are valid and added a
  loading state to prevent accidental double game creation.
- Kept the advanced setup screen available while making the simplified solo
  flow the default path for a new game.
- Standardized the new and advanced setup additions on English UI text.

### Campaigns

- Added a separate solo-oriented **Campaign** screen for starting a campaign
  or continuing a saved one.
- Made the current campaign scenario automatic while retaining simple starter
  deck selection and **Play / Continue Campaign** actions.
- Added campaign selection, stable campaign identifiers, saved campaign state,
  card previews, and improved MarvelCDB campaign deck imports.
- Added or completed campaigns for:
  - Mutant Genesis;
  - NeXt Evolution;
  - Age of Apocalypse;
  - Agents of S.H.I.E.L.D.;
  - Galaxy's Most Wanted;
  - The Mad Titan's Shadow.
- Audited campaign transitions and campaign card scripts, corrected Magneto's
  campaign power attachment, and applied remaining hero health correctly in
  standard campaign mode.
- The initial campaign implementation was integrated from
  [sdolle1775/marvel-lcg](https://github.com/sdolle1775/marvel-lcg) and then
  adapted, audited, and fixed for this fork.

### Heroes and player cards

- Added original integrations for **Echo**, **Wonder Man**, and **Daredevil**,
  including identities, hero cards, obligations, nemesis sets, metadata, and
  starter decks.
- Added Daredevil's separate Sense deck and exposed it as a labeled auxiliary
  player deck on the table.
- Completed Wonder Man's unfinished integration and corrected, among other
  behavior:
  - Mr. Hollywood resource generation and overpayment;
  - Ionic Psychology's contribution to hero attack;
  - Stronger Together defense and interruption flow;
  - Pacifism removal choices and readable obligation prompts;
  - ally, resource, discard, damage, and edge-case interactions.
- Added targeted Wonder Man card tests, system tests for indirect damage, and
  replay-oriented coverage for the new hero mechanics.
- Integrated the initial **Hercules** implementation from
  [sdolle1775/marvel-lcg](https://github.com/sdolle1775/marvel-lcg), then fixed
  its card scripts and setup behavior locally.
- Added and labeled Hercules' Labor and Gifts auxiliary decks, positioned them
  near the player area, and corrected the Protect Humanity initiator crash and
  other hero-specific timing/targeting issues.

### Replays and post-game flow

- Fixed **Save Replay** so completed games are persisted by the server instead
  of only reporting success in the browser.
- Added replay discovery, loading, downloading, and playback from the browser.
- Added an in-game replay control bar with first/previous/play-pause/next/last
  controls, a position counter, and a seek slider.
- Made replay playback open on the first recorded state and remain paused until
  the player starts it.
- Positioned the controls as a bottom-right overlay so they do not resize the
  table or cover the player's hand.
- Preserved deterministic step-forward, step-backward, seek, and restart
  behavior through the existing replay reconstruction model.
- Added a post-game **Try Again** action that starts the same setup with a new
  random seed.
- Excluded personal replay files and game notes from version control.

### Browser UI and controls

- Added an animation-speed slider to the advanced settings screen.
- Added readable descriptions beside advanced rule options.
- Fixed character encoding for the added settings text.
- Corrected keyboard shortcuts so they use the same guarded actions as pointer
  controls and respect disabled or paused states.
- Improved auxiliary deck rendering and labels for player-owned special decks.
- Made missing static resources such as `mask.svg` return a normal HTTP 404
  instead of crashing the file request handler with an assertion.
- Added clearer end-game statistics and replay actions without disturbing the
  game-table layout.

### Linux server and lifecycle

- Added `run.sh` as the preferred Linux launcher. It creates the virtual
  environment, installs requirements when needed, compiles stale TypeScript,
  checks port `2345`, and launches the server.
- Added missing runtime dependencies such as NumPy to the installation path.
- Added LAN-oriented binding so the Linux server can run on a small host while
  play happens in a browser on another device.
- Added [`marvel-lcg.service`](marvel-lcg.service) for a dedicated
  `marvel-lcg` system user and `/opt/marvel-lcg` working directory.
- Added [`INSTALL-SERVER.md`](INSTALL-SERVER.md) with installation, user,
  virtualenv, systemd, logging, and update instructions.
- Improved startup failure handling when the configured port is already in use
  and prevented crash saving from assuming a game object exists before engine
  initialization completes.
- Improved aiohttp shutdown and client-disconnect handling to reduce pending
  task and cleanup errors.

### Project documentation and maintenance

- Added [`AGENTS.md`](AGENTS.md) with architecture, validation, card scripting,
  frontend, replay, asset, and deployment guidance for coding agents.
- Added [`FORK-GOALS.md`](FORK-GOALS.md) to state the fork's concise priorities:
  simple solo play, a simplified UI, and reliable Linux hosting.
- Expanded the README progress section and added a current UI screenshot.
- Added the README progress image and documented which work originated in the
  community fork versus which hero integrations were developed locally.
- Updated ignore rules for downloaded assets, generated frontend files,
  runtime saves/replays/statistics/crashes, private notes, and local task files.

## Commit inventory

This is the complete committed history between the upstream baseline and the
current fork `master`, in ancestry order. The Rules Reference 1.8 work above is
committed separately on `feature/rules-v18` and therefore does not appear in
this `master` inventory.

- 2026-08-04 [`9a3fc26`] Add Linux server setup and UI improvements
- 2026-08-04 [`3a2c3b8`] Fix game hotkey handling
- 2026-08-04 [`4a2313f`] Add repository guidance for coding agents
- 2026-08-04 [`d5dac18`] Add streamlined solo game setup
- 2026-08-04 [`2900d19`] Add reliable replay saving and playback controls
- 2026-08-04 [`865ce56`] Add Echo hero pack integration
- 2026-08-05 [`7af3e5f`] Add Wonder Man hero pack integration
- 2026-08-05 [`fb5cbea`] Fix Wonder Man gameplay issues
- 2026-08-05 [`4702730`] Fix Wonder Man resource and attack handling
- 2026-08-05 [`d97935a`] Add Wonder Man card and replay tests
- 2026-08-05 [`99dc350`] Use English for game setup UI
- 2026-08-02 [`5f35b65`] Improve campaign card previews
- 2026-08-02 [`eb8d10c`] Implement Mutant Genesis campaign setup
- 2026-08-02 [`c01d20e`] Add campaign selector and identifiers
- 2026-08-02 [`30a9b07`] Implement NeXt Evolution campaign
- 2026-08-02 [`e9ce484`] Implement Age of Apocalypse campaign
- 2026-08-03 [`ed1bc29`] Implement Agents of SHIELD campaign
- 2026-08-03 [`c12c672`] Implement Galaxy's Most Wanted campaign
- 2026-08-03 [`d72195c`] Implement Mad Titan's Shadow campaign
- 2026-08-04 [`deaae23`] Fix Magneto campaign power attachment
- 2026-08-04 [`8b80803`] Audit campaign card transitions
- 2026-08-04 [`c3b00fb`] Audit all campaign card scripts
- 2026-08-05 [`1c515ca`] Apply campaign remaining health in standard mode
- 2026-08-05 [`2d8a204`] Improve MarvelCDB campaign deck imports
- 2026-08-05 [`239b727`] Integrate Hercules hero pack
- 2026-08-05 [`6e82ac5`] Add solo campaign flow and harden Hercules cards
- 2026-08-06 [`d58ca0a`] Add Daredevil hero integration
- 2026-08-06 [`3f5c403`] Document fork progress

## Compatibility and scope

- The supported target is solo play with one hero and a browser connected to a
  Linux-hosted server. Multiplayer and PvP expansion are not fork priorities.
- On the Rules Reference 1.8 development line, old saves and replays are not
  supported; only newly recorded `v18_all` data is accepted.
- Downloaded card art, local cache files, personal decks, saves, replays, and
  notes are intentionally not distributed by this repository.
- Generated JavaScript is not committed; TypeScript sources must be compiled
  during local setup or deployment.
