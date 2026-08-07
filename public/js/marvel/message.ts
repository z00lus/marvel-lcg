import { Command } from "./command.js";
import { Game } from "./game.js";
import { recordCampaignVictory } from "../campaign_state.js";
import { UserSettings } from "../user_settings.js";
import { Setting } from "./settings.js";

export class Message {

    private static overlay: HTMLElement
    private static messageElement: HTMLElement

    private static game_over_div: HTMLElement
    private static end_messageElement: HTMLElement
    private static end_messageElementText: HTMLElement
    private static retryButton: HTMLButtonElement
    private static saveReplayButton: HTMLButtonElement
    private static replaySavePromise: Promise<string>|null = null
    private static autoSaveAttempted = false

    private static async saveReplay(automatic: boolean) {
        if( Message.replaySavePromise ) {
            return Message.replaySavePromise
        }

        Message.saveReplayButton.disabled = true
        Message.saveReplayButton.innerHTML = '<i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Saving...'
        Message.replaySavePromise = Command.saveLocal()

        try {
            const path = await Message.replaySavePromise
            const label = automatic ? 'Autosaved' : 'Saved'
            Message.saveReplayButton.innerHTML = `<i class="fa fa-check" aria-hidden="true"></i> ${label}`
            return path
        } catch( error ) {
            console.error(error)
            Message.saveReplayButton.disabled = false
            Message.saveReplayButton.innerHTML = '<i class="fa fa-download" aria-hidden="true"></i> Save replay'
            throw error
        } finally {
            Message.replaySavePromise = null
        }
    }

    private static autoSaveReplay() {
        if( Message.autoSaveAttempted || Setting.replay_mode || !UserSettings.getAutoSaveReplays() ) {
            return
        }

        Message.autoSaveAttempted = true
        void Message.saveReplay(true).catch(() => {
            // Manual saving remains available after an autosave error.
        })
    }

    static init() {
        Message.overlay = document.getElementById('message-overlay')!;
        Message.messageElement = document.getElementById('message-text')!;

        Message.game_over_div = document.getElementById('game-over-box')!;
        // Message.end_overlay = document.getElementById('message-overlay')!;
        Message.end_messageElement = document.getElementById('game-over-text')!;
        Message.end_messageElementText = document.getElementById('game-over-text-2')!;
        const game_over_buttons = document.getElementById('game-over-buttons')!;

        Message.saveReplayButton = document.createElement('button');
        Message.saveReplayButton.innerHTML = '<i class="fa fa-download" aria-hidden="true"></i> Save replay';
        Message.saveReplayButton.classList.add('save-replay')
        Message.saveReplayButton.addEventListener('click', async function() {
            try {
                await Message.saveReplay(false)
            } catch( _ ) {
                // saveReplay already reports the error and restores the button.
            }
        });

        const buttonShare = document.createElement('button');
        buttonShare.innerHTML = '<i class="fa fa-cloud-upload" aria-hidden="true"></i> Share replay';
        buttonShare.classList.add('share-replay')
        buttonShare.addEventListener('click', function() {
            Command.uploadSave("Share")
        });

        Message.retryButton = document.createElement('button');
        Message.retryButton.innerHTML = '<i class="fa fa-repeat" aria-hidden="true"></i> Try again';
        Message.retryButton.classList.add('try-again');
        Message.retryButton.hidden = true;
        Message.retryButton.addEventListener('click', async function() {
            Message.retryButton.disabled = true;
            Message.retryButton.innerHTML = '<i class="fa fa-spinner fa-spin" aria-hidden="true"></i> Starting...';

            try {
                const response = await fetch('retry', { method: 'POST' });
                if( !response.ok ) {
                    throw new Error(`Retry failed: ${response.status}`);
                }
                Game.setGameOver(false);
            } catch( error ) {
                console.error(error);
                Message.retryButton.disabled = false;
                Message.retryButton.innerHTML = '<i class="fa fa-repeat" aria-hidden="true"></i> Try again';
            }
        });

        game_over_buttons.appendChild(Message.retryButton);
        game_over_buttons.appendChild(buttonShare);
        game_over_buttons.appendChild(Message.saveReplayButton);
    }

    static cleanGameOverMessage() {
        Message.game_over_div.classList.remove('active');
        Message.autoSaveAttempted = false
        Message.replaySavePromise = null
    }

    static showGameOverMessage(text: string) {
        Message.game_over_div.classList.add('active');
        Message.overlay.classList.remove('active');
        if( Game.players_won ) {
            Message.end_messageElement.textContent = "VICTORY";
            void recordCampaignVictory().catch((error) => {
                console.error('Could not update campaign progress', error)
            })
        } else {
            Message.end_messageElement.textContent = "DEFEAT";
        }
        Message.retryButton.hidden = Game.players_won;
        Message.retryButton.disabled = false;
        Message.retryButton.innerHTML = '<i class="fa fa-repeat" aria-hidden="true"></i> Try again';
        if( !Message.autoSaveAttempted && !Message.replaySavePromise ) {
            Message.saveReplayButton.disabled = false;
            Message.saveReplayButton.innerHTML = '<i class="fa fa-download" aria-hidden="true"></i> Save replay';
        }
        Message.end_messageElementText.textContent = text
        Message.autoSaveReplay()
    }

    static showMessage(text: string, original_duration: number|null = 1200) {
        // Show the overlay
        Message.overlay.classList.add('active');

        let duration = 1200
        if( original_duration != null ) {
            duration = original_duration
        }

        let sec = duration / 1000
        if( Game.game_over ) {
            Message.showGameOverMessage(text)
        } else
        if( original_duration == null ) {
            Message.messageElement.textContent = text;
            Message.overlay.style.animation = `overlay-move-once ${sec}s forwards`
        } else {
            Message.messageElement.textContent = text;
            Message.overlay.style.animation = `overlay-move ${sec}s forwards`
        }

        // Hide the overlay after the specified duration
        if( !Game.game_over && original_duration != null ) {
            setTimeout(() => {
                Message.overlay.style.animation = ""
                Message.overlay.classList.remove('active');
                // if( !Game.game_over ) {
                //     Message.game_over_div.classList.remove('active');
                // }
            }, duration);
        }
    }
}
