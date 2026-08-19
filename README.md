# Marvel Champions Digital: Ronin Edition

> Version 0.6.1 — “Echo”

> **This edition uses Marvel Champions Rules Reference v1.8 as its supported rules model.**

> [!CAUTION]
> **Please support the physical game.** Buy Marvel Champions and its expansions from Fantasy Flight Games, and support your friendly local game store whenever possible. Ronin Edition is intended as a testing, training, and learning platform—a convenient way to explore heroes, practise decks, and become familiar with the game—not as a replacement for the physical card game.

## New in 0.6.1: Fear No Evil

Five playable **Fear No Evil** scenario slices are now available in Quick Game:

- **Stop the Presses!** in Standard and Expert modes, with deterministic
  Daily Bugle Persona setup, all four stamina-powered Persona supports, and
  the required **Tombstone** and **Tracksuit Mafia** modular sets.
- **Protection Racket** in Standard and Expert modes, with all five selectable
  main schemes and the **Disasters** and **Tracksuit Mafia** modular sets.
- **The Getaway** scenario in Standard and Expert modes.
- **Art Museum Heist** in Standard and Expert modes, including its ART
  attachment flow and the required **The Owl** encounter set.
- **The Raft Breakout** in Standard and Expert modes, including **Master Key**,
  PRISONER setup, the required **Tombstone** encounter set, and all currently
  implemented underling choices.
- **Bullseye**, **Electro**, and **Purple Man** as selectable underlings, each
  with all three villain stages and full encounter sets. Purple Man includes
  his INFLUENCED minions, command obligations, and ally-control effects.
- The required **Cops** and **Drive** encounter sets.
- **Echo** and **Daredevil** starter decks and hero integrations.
- Clear `NEW` labels for the new scenarios, heroes, and underlings in Quick
  Game, with new scenarios shown first and the correct main-scheme previews.

This is an incremental integration of the expansion; additional Fear No Evil scenarios and content will follow as they are implemented and tested.

## Fork Goals

This fork focuses on a simple and convenient **solo Marvel Champions experience**.

- **Solo-first gameplay:** the primary use case is one player controlling one hero. Multiplayer and PvP are not development priorities.
- **Simplified UI:** starting a game should require only choosing a scenario, selecting a prepared hero deck, and pressing **Play**. Campaigns use a separate, equally simple flow.
- **Linux server:** the game is designed to run as a lightweight self-hosted server on Linux, with play happening from a desktop, tablet, or mobile browser over a trusted local network.

Development should prioritize rules correctness, reliable saves and replays, and improvements that make solo games easier to start and play.

## Snapshot

![](/docs/assets/image-6.png)

## Running

### Linux and macOS

Install Git, Python 3.10 or newer, and Node.js, then run:

```bash
git clone https://github.com/z00lus/marvel-lcg.git
cd marvel-lcg
./run.sh
```

`run.sh` creates the virtual environment, installs Python dependencies, compiles the frontend when necessary, and starts the server. Open `http://127.0.0.1:2345/` locally or `http://SERVER_IP:2345/` from another device on the same trusted network.

### Docker

From the cloned project directory, run:

```bash
docker compose up --build
```

Open `http://127.0.0.1:2345/`. Use `docker compose up --build -d` to run in the background and `docker compose stop` to stop it. Docker is also the recommended way to run the server on Windows.

The `runtime/` bind mount preserves statistics, campaign progress, the active **Continue Game** checkpoint, and QSave/Save 1–3 files across container rebuilds. Saved replays and downloaded assets are likewise preserved by their respective bind mounts.

### Collection and tabletop games

Open **Collection & Stats** from the main menu to mark the physical products you own, review digital and tabletop win rates, and track achievements. Use **Log Physical Game** to add a finished physical solo game. Manually logged games can be edited or deleted; statistics and achievement progress are recalculated automatically. All of this data is stored in the same `statistics.sqlite3` database used by digital game history.

#### Stopping and starting the Docker server

Temporarily stop the server while keeping its container:

```powershell
docker compose stop
```

Start the same container again without rebuilding it:

```powershell
docker compose start
```

Restart the running server:

```powershell
docker compose restart
```

`docker compose down` may also be used when you want to stop and remove the container and its Compose network. The next `docker compose up -d` recreates them. Project data remains in the `runtime/`, `replays/`, and `assets/` bind-mounted host directories. Running `down` is not required for a normal update, and `down -v` should be reserved for cases where Docker-managed volumes are intentionally being removed.

#### Updating on Windows with Docker Desktop

Open PowerShell in the existing cloned repository, update the source, and rebuild the service:

```powershell
git status --short
git pull --ff-only origin master
docker compose build --pull
docker compose up -d --remove-orphans
```

Continue Game is stored in `runtime/save_active_session.json`; QSave and Save 1–3 are stored in `runtime/save_0.json` through `runtime/save_3.json`. Because `runtime/` is mounted from the Windows host, these files survive container rebuilds and recreation.

If `git status` shows tracked local changes, preserve or commit them before pulling. Do not reset them blindly. Check the updated container with:

```powershell
docker compose ps
docker compose logs --tail=100 marvel-lcg
```

Open `http://127.0.0.1:2345/` and use `Ctrl+F5` if the browser still shows cached frontend files. Future updates only require `git pull --ff-only origin master`, `docker compose build --pull`, and `docker compose up -d --remove-orphans`. The `down -v` option is unnecessary for updates and should be used only when Docker-managed volumes are intentionally being removed.

## Progress

### Compared with upstream

Compared with the original [irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg), this fork currently adds:

- A Rules Reference **v1.8** engine update focused on solo rules correctness, including timing, status cards, damage, targeting, and ability initiation.
- Solo-first **Quick Game** and **Campaign** screens with prepared-deck selection, remembered choices, and optional Expert difficulty.
- A cohesive Ronin-themed interface with improved tablet and touch layouts, a settings screen, adjustable animation speed, and replay autosaving.
- Reliable replay saving, browsing, downloading, loading, step controls, timeline seeking, and paused-at-start playback.
- Unified SQLite history for digital, imported-replay, and manually logged physical games, with collection management, source filters, matchup statistics, and shared achievements.
- Manual and daily synchronization of public MarvelCDB deck IDs into a clearly marked user-deck collection.
- Better self-hosting through `run.sh`, Docker Compose, LAN-friendly defaults, a systemd unit, and Linux server documentation.

### Community integrations and new heroes

Campaign support and the initial Hercules implementation were merged from the [sdolle1775 fork](https://github.com/sdolle1775/marvel-lcg). The merged campaign work covers Mutant Genesis, NeXt Evolution, Age of Apocalypse, Agents of S.H.I.E.L.D., Galaxy's Most Wanted, and The Mad Titan's Shadow, together with related campaign-state fixes. After the merge, Hercules' special decks, card scripts, UI placement, and rules behavior were corrected in this fork and covered by focused tests.

The **Echo**, **Wonder Man**, and **Daredevil** hero integrations are original work created for this fork. They include starter decks, card scripts, special-deck handling where required, targeted tests, and ongoing replay-based playtesting.

Fear No Evil integration currently includes **Stop the Presses!**,
**Protection Racket**, **The Getaway**, **Art Museum Heist**, and **The Raft
Breakout**; the selectable **Bullseye**, **Electro**, and **Purple Man**
underlings; and the **Cops**, **Drive**, **The Owl**, **Tombstone**,
**Disasters**, and **Tracksuit Mafia** encounter sets. These scenario slices
include Standard and Expert setup plus focused rules and setup tests. Manual
solo replay validation continues as each new slice becomes playable.

Based on the original open-source [Marvel Champions: Digital Edition](https://irefrixs.itch.io/marvel-lcg) by Irefrixs.

## Security Warning

This game runs Python card scripts, which is not safe.  
Do not install or run any third-party card scripts unless you trust them.

这个游戏会运行用 Python 编写的卡牌脚本，这不安全。  
除非你完全信任，否则不要安装或运行任何第三方的卡牌脚本。
