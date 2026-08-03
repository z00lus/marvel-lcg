import { ButtonSetting, Setting } from './settings.js'
import { Game } from './game.js'
import { Effect } from './effect.js'
import { Music } from './music.js'
import { Client } from './client.js'
import { Lib } from './lib.js'
import { BtnOk } from './btn_ok.js'
import { Cards } from './cards.js'
import { Message } from './message.js'
import { centerDraggableDiv } from './draggable.js'

class ConnectionManager {
    private reconnectAttempts: number = 0;
    private maxReconnectAttempts: number = 5;
    private reconnectInterval: number = 1000; // Start with 1 second
    private retryTimerId: number | null = null;

    private lostConnectDiv: HTMLElement;
    private connectingText: HTMLElement;
    private waitConnectText: HTMLElement;
    private retryTimer: HTMLElement;
    private manualConnectDiv: HTMLElement;
    private seconds: number = 0
    private running: boolean = false
    private isPaused: boolean = false;

    constructor() {
        this.lostConnectDiv = document.getElementById('lost-connect')!;
        this.connectingText = document.getElementById('connecting')!;
        this.waitConnectText = document.getElementById('wait-connect')!;
        this.retryTimer = document.getElementById('retry-timer')!;
        this.manualConnectDiv = document.getElementById('manual-connect')!;
        let reconnectLink = document.getElementById('reconnect-link') as HTMLAnchorElement;
        let reconnectLink2 = document.getElementById('reconnect-link2') as HTMLAnchorElement;

        reconnectLink.addEventListener('click', (event) => {
            event.preventDefault();
            this.reconnectNow();
        });
        reconnectLink2.addEventListener('click', (event) => {
            event.preventDefault();
            this.reconnectNow();
        });
    }

    public pause() {
        this.isPaused = true
    }

    public unpause() {
        this.isPaused = false
    }

    public onLostConnect(): void {
        this.lostConnectDiv.classList.remove('hide')
        this.startReconnect();
    }

    public onConnected(): void {
        this.lostConnectDiv.classList.add('hide')
        this.stopReconnect();
        console.log("Reconnected successfully!");
    }

    private startReconnect(): void {
        this.attemptReconnect();
    }

    private attemptReconnect(): void {
        if( this.running ) {
            return
        }
        this.running = true

        const connect = () => {
            if( this.retryTimerId ) {
                clearTimeout(this.retryTimerId);
                this.retryTimerId = null;
            }
            this.reconnectAttempts++;
            this.reconnectInterval *= 2;
            this.showConnectingPrompt();
            this.running = false
            UI.doReconnect();
        }

        if( this.reconnectAttempts == 0 ) {
            connect()
        }
        else
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.seconds = Math.round(this.reconnectInterval / 1000)
            this.connectingText.classList.add('hide')
            this.manualConnectDiv.classList.add('hide')
            this.retryTimer.textContent = this.seconds.toString();
            this.waitConnectText.classList.remove('hide')

            if( this.retryTimerId == null ) {
                this.retryTimerId = setInterval(() => {
                    if( !this.isPaused ) {
                        this.seconds -= 1;
                        if( this.seconds <= 0 ) {
                            connect()
                        } else {
                            this.retryTimer.textContent = this.seconds.toString();
                        }
                    }
                }, 1000)
            }
        } else {
            this.connectingText.classList.add('hide')
            this.waitConnectText.classList.add('hide')
            this.manualConnectDiv.classList.remove('hide')
            console.log("Max reconnect attempts reached.");
        }
    }

    private showConnectingPrompt(): void {
        this.connectingText.classList.remove('hide')
        this.waitConnectText.classList.add('hide')
    }

    private stopReconnect(): void {
        this.reconnectAttempts = 0; // Reset attempts
        this.reconnectInterval = 1000; // Reset interval
        this.running = false
        this.lostConnectDiv.classList.add('hide')
        this.connectingText.classList.add('hide')
        this.waitConnectText.classList.add('hide')
        this.manualConnectDiv.classList.add('hide')
        this.seconds = 0
        if( this.retryTimerId ) {
            clearInterval(this.retryTimerId);
            this.retryTimerId = null;
        }
    }

    public reconnectNow(): void {
        this.stopReconnect()
        this.onLostConnect();
    }
}

class PromptBox {
    private static prompt_box_div = document.getElementById('prompt-box-container') as HTMLElement
    private static prompt_text_div = document.getElementById('prompt-text') as HTMLElement
    private static prompt_box_lock = document.getElementById('prompt-box-lock') as HTMLElement
    private static game_over_text = "<div class='game-over'>--- Game Over ---</div>"
    private static prompt_text     = ""

    static {
        document.querySelector<HTMLElement>('#prompt-box-close')!.onclick = () => {
            PromptBox.cleanPromptText()
        }

        PromptBox.prompt_box_lock.onclick = (e) => {
            const btn = e.target as HTMLElement
            btn.classList.toggle('locked')
        }
    }

    ////////////////////////////////////////////////////////////////////////////////
    // Prompt
    static cleanPromptText() {
        PromptBox.prompt_box_div.classList.add("hide");
    }

    static restartPromptTextAnimation() {
        // https://css-tricks.com/restart-css-animation/
        PromptBox.prompt_box_div.classList.remove("prompt-anime");
        // Use a timeout to re-add the class after a short delay
        requestAnimationFrame(() => {
            PromptBox.prompt_box_div.classList.add("prompt-anime");
        });
    }

    static setPromptGameOver() {
        PromptBox.setTempPromptText(PromptBox.game_over_text, false)
    }

    static setPromptWait() {
        Game.setGameOver(false)
        // UI.please_wait = true
        // if( Game.current_step_id > 1 ) {
        //     Message.showMessage("Please wait", null)
        // }
    }

    static setPromptText(text: string) {
        if( text ) {
            PromptBox.prompt_text = text
            PromptBox.setTempPromptText(text, false)
        } else {
            PromptBox.resetPromptText()
        }
    }

    static setTempPromptText(text: string, add_on_event=true) {
        // PromptBox.prompt_text_div.classList.remove('none-events')
        if( text ) {
            // add_on_event = false
            const is_in_play_turn = UI.is_in_play_turn
            if( add_on_event && is_in_play_turn ) {
                add_on_event = false
            }
            if( !add_on_event || is_in_play_turn ) {
                if( text != PromptBox.prompt_text_div.innerHTML ) {
                    PromptBox.prompt_text_div.innerHTML = text
                }
            } else {
                PromptBox.prompt_text_div.innerHTML = PromptBox.prompt_text + "<hr/>" + text
                // PromptBox.prompt_text_div.classList.add('none-events')
            }
            PromptBox.restartPromptTextAnimation()
            PromptBox.prompt_box_div.classList.remove('hide')
            if( PromptBox.prompt_box_lock.classList.contains('locked') ) {
                centerDraggableDiv(PromptBox.prompt_box_div)
            }
        } else {
            PromptBox.resetPromptText(true)
        }
    }

    static resetPromptText(hide=false) {
        if( UI.is_in_play_turn || hide ) {
            PromptBox.prompt_box_div.classList.add('hide')
        } else {
            PromptBox.setTempPromptText(PromptBox.prompt_text, false)
        }
    }
}

////////////////////////////////////////////////////////////////////////////////
//
export class UI {
    static btn_end_div      = document.getElementById('btn-end') as HTMLButtonElement;
    static btn_ok_div       = document.getElementById('btn-ok') as HTMLButtonElement;
    static prompt           = PromptBox

    private static top_bar_div?    = document.getElementById('top-bar') as HTMLElement
    static event_name      = ""
    static is_in_play_turn = false
    private static slider_div      = document.getElementById("delay-range") as HTMLTextAreaElement;
    private static delay_time      = 400
    
    static last_game_id    = -1
    static version         = Lib.cookie.getString("app_version")

    static last_phase_text = ""
    static please_wait = false

    private static hand_card_margin_div         = document.getElementById("hand-card-margin") as HTMLTextAreaElement;
    private static hand_card_total_deg          = document.getElementById("hand-card-total-deg") as HTMLTextAreaElement;
    private static hand_card_margin_bottom_div  = document.getElementById("hand-card-margin-bottom") as HTMLTextAreaElement;
    private static anime_time_div               = document.getElementById("anime-time") as HTMLInputElement;
    private static phase_div                    = document.querySelector('#phase') as HTMLElement
    private static current_div = document.querySelector("#current-round") as HTMLInputElement

    private static iframe                       = document.getElementById("weather-background") as HTMLIFrameElement;
    static weather              = ""

    static anime_time           = 0 // second
    static anime_move_time      = 0
    static anime_shuffle_time   = 0
    static anime_time_card      = 0

    static error_occurred_text  = ""

    static hold_ctrl    = false
    static hold_alt     = false
    static hold_shift   = false

    static temp_sorted_deck_div: HTMLElement|null = null
    static tempSortDeck(sort: boolean) {
        function getObjectId() {
            let object_id = null
            function can_sort() {
                if( !UI.temp_sorted_deck_div ) {
                    return false
                }
                if( Game.game_over ) {
                    return true
                }
                if( Setting.is_debug ) {
                    return true
                }
                const classesToCheck = ['player-deck', 'additional-deck', 'encounter-deck'];
                return !classesToCheck.some(className => UI.temp_sorted_deck_div!.classList.contains(className));
                // return  !UI.temp_sorted_deck_div!.classList.contains('player-deck') &&
                //         !UI.temp_sorted_deck_div!.classList.contains('additional-deck') &&
                //         !UI.temp_sorted_deck_div!.classList.contains('encounter-deck')
            }
            if( can_sort() ) {
                const card_div = UI.temp_sorted_deck_div!.querySelector<HTMLElement>('.card')
                if( card_div ) {
                    object_id = Number(card_div.dataset.id!)
                }
            }
            return object_id
        }

        let object_id = getObjectId()
        if( object_id ) {
            if( !sort ) {
                let a = 1
            }
            Cards.render.printDeckWhenHighlightTarget([object_id], sort)
        }
    }

    static global_first_create = true

    static anime_move_cards_count = 0
    static anime_shuffle_cards_count = 0

    static background_image_normal = `linear-gradient(0deg, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 100%)`
    static background_image_super_rare = `linear-gradient(120deg, #ff0084FF 15%, #fca400FF 30%, #ffff00FF 40%, #00ff8aFF 60%, #00cfffFF 70%, #cc4cfaFF 85%)`
    static background_image_ultra_rare = `linear-gradient(0deg, rgba(255,255,255,0) 0%, gold 100%)`

    static debug_text: string = ""

    static connection_manager = new ConnectionManager();

    static async init() {
        document.querySelectorAll<HTMLElement>('.area').forEach( div => {
            div.oncontextmenu = (event) => {
                event.stopPropagation()
                event.preventDefault()
            }
        })

        document.querySelector(`#version`)!.innerHTML = UI.version

        UI.hand_card_margin_bottom_div.oninput = function() {
            let element = document.querySelector('#hand-cards') as HTMLElement
            element.style.setProperty('--margin-bottom', `${UI.hand_card_margin_bottom_div.value}vw`)
            console.log(UI.hand_card_margin_bottom_div.value)
        }
        UI.hand_card_margin_div.oninput = function() {
            let element = document.querySelector('#hand-cards') as HTMLElement
            element.style.setProperty('--card-margin', `${UI.hand_card_margin_div.value}vw`)
            console.log(UI.hand_card_margin_div.value)
        }
        UI.hand_card_total_deg.oninput = function() {
            let element = document.querySelector('#hand-cards') as HTMLElement
            element.style.setProperty('--total-deg', `${UI.hand_card_total_deg.value}deg`)
        }
        UI.delay_time = Number(UI.slider_div.value)
        UI.slider_div.oninput = UI.resetDelayTime

        const animationTimeStorageKey = 'marvel_lcg_animation_time';
        const savedAnimationTime = Number(localStorage.getItem(animationTimeStorageKey));
        if( savedAnimationTime >= Number(UI.anime_time_div.min) &&
            savedAnimationTime <= Number(UI.anime_time_div.max) ) {
            UI.anime_time_div.value = savedAnimationTime.toString();
        }

        UI.anime_time_div.oninput = () => {
            UI.updateAnimeTime();
            localStorage.setItem(animationTimeStorageKey, UI.anime_time_div.value);
        }

        UI.updateAnimeTime()

        UI.hideAllTimerBar()

        UI.updateCurrentPlayer(Setting.player_id)
    }

    static setDebugMessage(category: 'debug'|'world'|'card', text: string) {
        if( category == 'debug' || category == 'world' ) {
            return
        }
        UI.debug_text = text
        const debugText = new CustomEvent('debugText', {});
        window.dispatchEvent(debugText);
    }

    static drawLine(divA: HTMLElement, divB: HTMLElement, class_name='target', timeout=1500) {
        // Get the positions and dimensions of the divs
        const rectA = Lib.client.getOffset(divA);
        const rectB = Lib.client.getOffset(divB);

        // Calculate the center points
        const x1 = rectA.left   + divA.offsetWidth / 2;
        const y1 = rectA.top    + divA.offsetHeight / 2;
        const x2 = rectB.left   + divB.offsetWidth / 2;
        const y2 = rectB.top    + divB.offsetHeight / 2;

        // Calculate the length and angle
        const length = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
        const angle = Math.atan2(y2 - y1, x2 - x1); // Angle in radians
        const angleInDegrees = angle * (180 / Math.PI); // Convert to degrees

        // Create the arrow element
        const arrow = document.createElement('div');
        const arrow_anime = document.createElement('div');
        arrow_anime.classList.add('target-arrow');
        arrow_anime.classList.add(class_name);

        arrow.appendChild(arrow_anime)
        arrow.classList.add('target-arrow-box');
        arrow.style.position = 'absolute';
        arrow.style.width = '0';
        arrow.style.transformOrigin = '0 0';

        // Set the initial position and rotation of the arrow
        arrow.style.left = `${x1}px`;
        arrow.style.top = `${y1}px`;
        // arrow.style.transform = `rotate(${angle}rad) scaleX(0)`;
        arrow.style.transform = `rotate(${angleInDegrees}deg) translateZ(10px)`;

        // Append the arrow to the body
        document.body.querySelector('#scene')!.appendChild(arrow);

        requestAnimationFrame(() => {
            // void arrow.offsetWidth; // Trigger reflow
            // Trigger the animation
            requestAnimationFrame(() => {
                // arrow.style.transform = `rotate(${angle}rad) scaleX(1)`;
                arrow.style.width = `${length}px`;
            });

            // Remove the arrow after the timeout
            setTimeout(() => {
                arrow_anime.classList.add('remove');
                arrow_anime.style.width = `0`;
                setTimeout(() => {
                    arrow.remove();
                }, UI.anime_time * timeout * .5);
            }, UI.anime_time * timeout * 1);
        });
    }

    static firstGameSync() {
        // UI.first_game_sync = true
        UI.changeWeather('')
        // UI.focusOnPlayer(1)
    }

    // [0,1,2,3]
    static focusOnPlayer(id: number) {
        let player_index = id

        if( Game.forced_on_player == player_index ) {
            return
        }

        let areas: HTMLElement[] = []
        for (let j = 0; j <= 3; j++) {
            // Select the player element
            const playerElements = document.querySelectorAll<HTMLElement>(`.player-${j}`);
            // Loop through each selected element and add the 'hide' class
            playerElements.forEach(playerElement => {
                if (j === id) {
                    // playerElement.classList.remove('hide-player');
                    areas.push(playerElement)
                } else {
                    playerElement.classList.add('hide-player');
                }
            });
        }
        // MoveCard.doMoveFocusOnPlayer(areas)
        for( const area of areas ) {
            area.classList.remove('hide-player');
        }
        Game.forced_on_player = player_index
        UI.updateCurrentPlayer(player_index)

        Cards.render.printCards()
        Effect.updateHighLight()
    }

    static updateAnimeTime() {
        if( UI.hold_ctrl ) {
            UI.anime_time = .01
        } else {
            UI.anime_time = parseFloat(UI.anime_time_div.value)
        }
        UI.anime_move_time = UI.anime_time * 1.5
        UI.anime_shuffle_time = UI.anime_time * 4
        UI.anime_time_card = UI.anime_time * 4
        document.body.style.setProperty('--anime-time', `${UI.anime_time}s`)
        document.body.style.setProperty('--anime-move-time', `${UI.anime_move_time}s`)
        document.body.style.setProperty('--anime-shuffle-time', `${UI.anime_shuffle_time}s`)
        document.body.style.setProperty('--anime-time-card', `${UI.anime_time_card}s`)
    }
    static resetDelayTime() {
        UI.delay_time = Number(UI.slider_div.value);
    }
    static getDelayTime() {
        let value = parseFloat(UI.anime_time_div.value) * 2000 + 100
        return value
    }
    static addDelayTime(time: number) {
        UI.delay_time += time
    }

    static setPhaseText(text: string) {
        UI.phase_div.dataset.phase = text
    }

    ////////////////////////////////////////////////////////////////////////////////
    // Message
    static cleanMessage() {
        const overlay = document.getElementById('message-overlay')!;
        overlay.style.animation = ""
        overlay.classList.remove('active');
    }

    ////////////////////////////////////////////////////////////////////////////////
    //
    static setTurnId(round: number, step: number) {
        UI.current_div.innerHTML = `Round ${round} Step ${step}`

        let phase_text = ""
        if( Game.game_over ) {
            phase_text = "Game Over";
        } else {
            phase_text = Game.world_descriptor.phase
        }

        let waiting = false

        if( !UI.please_wait && UI.last_phase_text == phase_text) {
            return 0
        }
        if( UI.please_wait ) {
            waiting = true
            UI.please_wait = false
        }

        const last_phase_text = UI.last_phase_text
        UI.last_phase_text = phase_text
        let text = ""
        if( round > 0 && !Game.game_over ){
            text = `${phase_text} (${round})`
        } else {
            text = `${phase_text}`
        }
        let text_div = UI.top_bar_div?.querySelector<HTMLElement>("#turn-id")
        if( text_div ) {
            text_div.innerHTML = text
        }

        if( !["Initialize",
            "Init Finished",
            "End Phase",
            "End Round",
            "Start Round",
        ].includes(phase_text) ) {
            let ms = 1000
            if( Game.game_over ) {

                function extractBooleanAndCleanString(input: string): { cleanedString: string; boolValue: boolean } {
                    // Regular expression to match the ending "\nTrue" or "\nFalse"
                    const regex = /\n(True|False)$/;
                    const match = input.match(regex);
                
                    if (match) {
                        // Extract the boolean value from the match
                        const boolValue = match[1] === 'True';
                        
                        // Remove the matched part from the original string
                        const cleanedString = input.replace(regex, '');
                        
                        return { cleanedString, boolValue };
                    }
                
                    // If no match is found, return the original string and a default boolean value
                    return { cleanedString: input, boolValue: false };
                }
                const result = extractBooleanAndCleanString(Game.world_descriptor.prompt_last_text)
                Game.world_descriptor.prompt_last_text = result.cleanedString
                Game.players_won = result.boolValue
                phase_text = Game.world_descriptor.prompt_last_text.replace(/^\s*--- Game Over ---\s*(.+)$/m, "$1");
            }
            if( phase_text ) {
                Message.showMessage(phase_text, ms)
            }
            // Button.enableUndo()
            // if( waiting ) {
            //     return 0
            // } else {
            //     return ms
            // }
            return 0
        } else {
            if( last_phase_text == "Game Over" ) {
                UI.cleanMessage()
            }
            return 0
        }
    }

    static update() {
        if( Effect.response_json_ask?.options.length ) {
            BtnOk.setDisable(false)
            BtnOk.setCancel('')
            Effect.updateHighLight()
        } else {
            BtnOk.setDisable(true)
        }
    }

    ////////////////////////////////////////////////////////////////////////////////
    //
    static selectCountClear() {
        for(const card_div of document.querySelectorAll<HTMLElement>('.card')) {
            card_div.setAttribute('select-count', "");
        }
    }

    static onLostConnect() {
        Music.pauseBgm()
        Game.is_lost_connect = true
        UI.connection_manager.onLostConnect()
    }

    static onConnected() {
        Game.is_lost_connect = false;
        UI.connection_manager.onConnected()
    }

    static doReconnect() {
        Client.doConnect()
    }

    ////////////////////////////////////////////////////////////////////////////////
    // Timer bar / Time bar
    static hideAllTimerBar() {
        for(let i of [0,1,2,3]) {
            const div = document.querySelector<HTMLElement>(`#player-${i}-btn`)!
            div?.classList.remove('active');
            let bar = div?.querySelector<HTMLElement>(`.progress-bar`)
            if( bar ) {
                bar.remove()
            }
        }
    }

    static updateTimerBar(remaining_time: number, max_timeout: number, round: number, step: number) {
        // console.log(rate)
        let pre = (remaining_time / max_timeout * 100)

        for( let i of Game.asking_players ) {
            const div = document.querySelector<HTMLElement>(`#player-${i}-btn`)
            if( div ) {
                div.classList.add('active');
                let bar = div.querySelector<HTMLElement>(`.progress-bar`)
                if( max_timeout != 0 ) {
                    if( !bar ) {
                        bar = document.createElement('div')
                        bar.className = "progress-bar"
                        div.appendChild(bar)
                    }
                    ((the_bar: HTMLElement) => {
                        the_bar.style.transitionDuration = `0s`
                        the_bar.style.width = `${pre}%`
                        void the_bar.offsetWidth;
                        the_bar.style.transitionDuration = `${remaining_time}s`
                        requestAnimationFrame(() => {
                            the_bar.style.width = "0"
                        })
                    })(bar)
                } else {
                    if( bar ) {
                        bar.remove()
                    }
                }
            }
        }
    }

    ////////////////////////////////////////////////////////////////////////////////
    // Weather
    static changeWeather(weather: string, forced: boolean=false) {
        if ( forced || UI.weather != weather ) {
            if( !ButtonSetting.enable_enhance_fx ) {
                UI.iframe.src = "";
            } else {
                UI.weather = weather
                if( weather ) {
                    UI.iframe.src = `/effects/weather/${weather}.html`;
                } else {
                    UI.iframe.src = "";
                }
            }
        }
    }

    static updateCurrentPlayer(player_id: number|0|1|2|3) {
        document.body.classList.remove('current_player_0')
        document.body.classList.remove('current_player_1')
        document.body.classList.remove('current_player_2')
        document.body.classList.remove('current_player_3')

        document.body.classList.add(`current_player_${player_id}`)
    }
}

(window as any).UI = UI;
