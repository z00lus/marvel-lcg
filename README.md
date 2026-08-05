# Fork Goals

This fork focuses on a simple and convenient **solo Marvel Champions experience**.

- **Solo-first gameplay:** the primary use case is one player controlling one hero. Multiplayer and PvP are not development priorities.
- **Simplified UI:** starting a game should require only choosing a scenario, selecting a prepared hero deck, and pressing **Play**. Campaigns use a separate, equally simple flow.
- **Linux server:** the game is designed to run as a lightweight self-hosted server on Linux, with play happening from a desktop, tablet, or mobile browser over a trusted local network.

Development should prioritize rules correctness, reliable saves and replays, and improvements that make solo games easier to start and play.

# Progress

## Compared with upstream

Compared with the original [irefrixs/marvel-lcg](https://github.com/irefrixs/marvel-lcg), this fork currently adds:

- A solo-first **Quick Game** screen with scenario and bundled starter-deck selection, remembered choices, input validation, and double-start protection.
- A separate simplified **Campaign** flow for starting or continuing a solo campaign.
- Better Linux self-hosting through `run.sh`, LAN-friendly defaults, a systemd unit, and server installation documentation.
- UI improvements including adjustable animation speed, clearer rule descriptions, corrected keyboard shortcuts, and a **Try Again** action after defeat.
- Reliable replay saving after a completed game, browser listing and download, correct replay loading, and an overlay control bar with first/previous/play-pause/next/last controls and timeline seeking. Replays now open paused and no longer resize or distort the game board.

## Community integrations and new heroes

Campaign support and the initial Hercules implementation were merged from the [sdolle1775 fork](https://github.com/sdolle1775/marvel-lcg). The merged campaign work covers Mutant Genesis, NeXt Evolution, Age of Apocalypse, Agents of S.H.I.E.L.D., Galaxy's Most Wanted, and The Mad Titan's Shadow, together with related campaign-state fixes. After the merge, Hercules' special decks, card scripts, UI placement, and rules behavior were corrected in this fork and covered by focused tests.

The **Echo**, **Wonder Man**, and **Daredevil** hero integrations are original work created for this fork. They include starter decks, card scripts, special-deck handling where required, targeted tests, and ongoing replay-based playtesting.

Original open-source of Marvel LCG digital version on [ITCH](https://irefrixs.itch.io/marvel-lcg)
                        | How to use the card editor        |

## Security Warning

This game runs Python card scripts, which is not safe.  
Do not install or run any third-party card scripts unless you trust them.

这个游戏会运行用 Python 编写的卡牌脚本，这不安全。  
除非你完全信任，否则不要安装或运行任何第三方的卡牌脚本。

## Snapshot

![](/docs/assets/image-4.png)
