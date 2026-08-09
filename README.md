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

Open `http://127.0.0.1:2345/`. Use `docker compose up --build -d` to run in the background and `docker compose down` to stop it. Docker is also the recommended way to run the server on Windows.

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
