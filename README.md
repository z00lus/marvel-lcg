# Marvel Champions Digital: Ronin Edition

> Version 0.6.0 — “Echo”

> **This edition uses Marvel Champions Rules Reference v1.8 as its supported rules model.**

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

Open PowerShell in the existing cloned repository.

**ONLY for the first update from an older build:** preserve any active Continue/QSave files if needed. Copy them from the old container into a temporary migration directory before rebuilding:

```powershell
New-Item -ItemType Directory -Force .\save-migration | Out-Null
docker cp marvel-lcg:/app/save_active_session.json .\save-migration\save_active_session.json
docker cp marvel-lcg:/app/save_0.json .\save-migration\save_0.json
```

Either `docker cp` command may report that the file does not exist when there is no active Continue checkpoint or QSave. The same command can be used for `save_1.json`, `save_2.json`, or `save_3.json` when those slots are needed.

Update the source and rebuild the image:

```powershell
git status --short
git pull --ff-only origin master
docker compose build --pull
```

After upgrading from that older build, place the preserved files into the corresponding persistent `runtime/` directory, then recreate the service:

```powershell
New-Item -ItemType Directory -Force .\runtime | Out-Null
if (Test-Path .\save-migration\save_active_session.json) { Copy-Item .\save-migration\save_active_session.json .\runtime\save_active_session.json }
if (Test-Path .\save-migration\save_0.json) { Copy-Item .\save-migration\save_0.json .\runtime\save_0.json }
docker compose up -d --remove-orphans
```

Repeat the conditional `Copy-Item` command for `save_1.json`, `save_2.json`, or `save_3.json` when those slots were preserved. This migration is needed only for the first update from an older build. Future builds save Continue and all numbered QSave files directly in `runtime/`, so these copy steps do not need to be repeated.

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
- Manual and daily synchronization of public MarvelCDB deck IDs into a clearly marked user-deck collection.
- Better self-hosting through `run.sh`, Docker Compose, LAN-friendly defaults, a systemd unit, and Linux server documentation.

### Community integrations and new heroes

Campaign support and the initial Hercules implementation were merged from the [sdolle1775 fork](https://github.com/sdolle1775/marvel-lcg). The merged campaign work covers Mutant Genesis, NeXt Evolution, Age of Apocalypse, Agents of S.H.I.E.L.D., Galaxy's Most Wanted, and The Mad Titan's Shadow, together with related campaign-state fixes. After the merge, Hercules' special decks, card scripts, UI placement, and rules behavior were corrected in this fork and covered by focused tests.

The **Echo**, **Wonder Man**, and **Daredevil** hero integrations are original work created for this fork. They include starter decks, card scripts, special-deck handling where required, targeted tests, and ongoing replay-based playtesting.

Based on the original open-source [Marvel Champions: Digital Edition](https://irefrixs.itch.io/marvel-lcg) by Irefrixs.

## Security Warning

This game runs Python card scripts, which is not safe.  
Do not install or run any third-party card scripts unless you trust them.

这个游戏会运行用 Python 编写的卡牌脚本，这不安全。  
除非你完全信任，否则不要安装或运行任何第三方的卡牌脚本。
