import { Setting } from './settings.js'
import { UI } from './ui.js'
import { HoverCard } from './hover.js'
import { Button } from './buttons.js'
import { HistoryLog } from './history.js'
import { Replay } from './replay.js'
import { SelectStep } from './select.js'
import { Effect } from './effect.js'

///////////////////////////////////////////////////////////////////////////////
// Do
export class WindowLoad {
    static mouse_y = 0
    static mouse_x = 0

    static onClick(event: MouseEvent) {
        document.querySelectorAll('.deck.clicked').forEach( div => {
            div.classList.remove('clicked')
            if( UI.temp_sorted_deck_div ) {
                UI.tempSortDeck(false)
                UI.temp_sorted_deck_div = null
            }
        })
    }

    static onKeyUp(event: KeyboardEvent) {
        if (!event.altKey) {
            UI.hold_alt = false
            document.body.classList.remove('hold-alt')
        }
        if( !event.ctrlKey ) {
            UI.hold_ctrl = false
            UI.updateAnimeTime()
            document.querySelector("#skipping-icon")!.classList.add('hide')
            document.body.classList.remove('hold-ctrl')
            // console.log('ctrl_key up')
        }
        if( !event.shiftKey ) {
            UI.hold_shift = false
            // UI.tempSortDeck(false)
            // UI.temp_sorted_deck_div = null
        }
    }

    static onKeyDown(event: KeyboardEvent) {
        if (event.altKey) {
            UI.hold_alt = true
            document.body.classList.add('hold-alt')
        }
        if (event.ctrlKey) {
            document.body.classList.add('hold-ctrl')
        }
        if( event.shiftKey ) {
            
            if( UI.hold_shift == false ) {
                if( UI.temp_sorted_deck_div ) {
                    UI.tempSortDeck(false)
                }
            }

            UI.hold_shift = true
            UI.temp_sorted_deck_div = document.querySelector('.deck.clicked')
            UI.tempSortDeck(true)
        }

        if( event.key == "Pause" ) {
            Button.togglePause()
            event.preventDefault();
        }
        else
        if( event.ctrlKey ) {
            // ctrl + s
            if (event.key === 's') {
                event.preventDefault();
                Button.doSave(0)
            }
            else
            // ctrl + shift + z
            if (event.key.toLowerCase() === 'z' && event.shiftKey ) {
                event.preventDefault();
                Button.doOldUndo()
            }
            else
            // ctrl + z
            if (event.key === 'z') {
                event.preventDefault();
                Button.doUndo()
            }
            else
            // ctrl + y
            if (event.key === 'y') {
                event.preventDefault();
                // Button.doRedo()
                Replay.doReplay(true)
            }
            else
            // ctrl + q
            if (event.key === 'q') {
                event.preventDefault();
                Replay.doReplay()
                Button.doToEnd()
            }
            else
            // // ctrl + r
            // if (event.key === 'r') {
            //     event.preventDefault();
            //     Button.toggleReplay()
            // }
            // else
            // ctrl + e
            if (event.key === 'e') {
                event.preventDefault();
                Replay.doReplay()
            }
            else
            if( event.ctrlKey ) {
                UI.hold_ctrl = true
                UI.updateAnimeTime()
                HoverCard.hide()
                // if( HoverCard.center_preview.has_image ) {
                //     Button.disablePause()
                // }
                document.querySelector("#skipping-icon")!.classList.remove('hide')
            }
        }
        else {
            if( event.key === "F1"){
                UI.focusOnPlayer(0)
                event.preventDefault();
            }
            else
            if( event.key === "F2"){
                UI.focusOnPlayer(1)
                event.preventDefault();
            }
            else
            if( event.key === "F3"){
                UI.focusOnPlayer(2)
                event.preventDefault();
            }
            else
            if( event.key === "F4"){
                UI.focusOnPlayer(3)
                event.preventDefault();
            }
            else
            if (event.key === "Tab") {
                Button.doToggleHistory()
                event.preventDefault();
            }
            else
            if( event.key === "1" ){
                let deck_div = document.querySelector(`.deck.player-${Setting.player_id}.player-deck`) as HTMLElement
                deck_div.classList.toggle('clicked')
                event.preventDefault();
            }
            else
            if( event.key === "2" ){
                let deck_div = document.querySelector(`.deck.player-${Setting.player_id}.player-discard-pile`) as HTMLElement
                deck_div.classList.toggle('clicked')
                event.preventDefault();
            }
            else
            if( event.key === "3" ){
                let deck_div = document.querySelector(`.deck.player-${Setting.player_id}.additional-deck`) as HTMLElement
                deck_div.classList.toggle('clicked')
                event.preventDefault();
            }
            else
            if( event.key === "4" ){
                let deck_div = document.querySelector(`.deck.player-${Setting.player_id}.additional-discard-pile`) as HTMLElement
                deck_div.classList.toggle('clicked')
                event.preventDefault();
            }
            // if (event.key === "2") {
            //     document.getElementsByTagName('iframe')[0].classList.toggle('hide')
            // }
            else
            if( event.key == "+" ) {
                event.preventDefault();
                Replay.doReplay(true, 1, true)
            }
            else
            if (event.key === "Enter") {
                if( !SelectStep.isCard() ) {
                    Button.doBtnOk()
                }
                event.preventDefault();
            }
            else
            if (event.key === "Escape") {
                if( HistoryLog.isOpen() ) {
                    HistoryLog.toggle()
                }
                if( HoverCard.center_preview.has_image ) {
                    Button.disablePause()
                }
                // else
                // if( (SelectStep.isTargets() || SelectStep.isCost()) && 
                //     Effect.select_effect_obj.selected_targets.length > 0 ) {
                //     Effect.onCancel()
                // }
                else
                if( Effect.isExEffect() && (SelectStep.isTargets() || SelectStep.isCost()) && Effect.select_effect_obj.selected_targets.length > 0 ) {
                    Button.disablePause()
                    Effect.onCancel()
                }
                else
                if( SelectStep.isCard() ||
                    Effect.isExEffect() && (SelectStep.isTargets() || SelectStep.isCost()) && Effect.select_effect_obj.selected_targets.length == 0 ||
                    // Effect.isExEffect() && (SelectStep.isTargets() || SelectStep.isCost()) ||
                    Effect.isExEffect() && SelectStep.isEffect() ||
                    Effect.is_in_event == 'response' ||
                    Effect.is_in_event == 'interrupt'
                ) {
                    Button.doRedo()
                    // Replay.doReplay(true)
                }
                else {
                    Button.doBtnCancel()
                }
                event.preventDefault();
            }
            else
            if (event.key === "Tab") {
                Button.doToggleHistory()
                event.preventDefault();
            }
            else
            if (event.key === " " ) {
                Button.togglePause()
                event.preventDefault();
            }
            else
            if (event.key === "Alt" ) {
                event.preventDefault();
            }
            else
            if (event.key === 'Backspace') {
                event.preventDefault();
                Button.doToEnd()
            }
            else
            if (event.key === "q") {
                HoverCard.rotate(-1)
                event.preventDefault();
            }
            else
            if (event.key === "e" || event.key === "r" ) {
                HoverCard.rotate(+1)
                event.preventDefault();
            }
            else
            if (event.key === "f" ) {
                HoverCard.flip()
                event.preventDefault();
            }
        }
    };

    static {
        window.oncontextmenu = function(event) {
            if( !event.shiftKey ) {
                return false;
            }
        }
        window.onmousemove = (event) => {
            // console.log(event.clientX, event.clientY)
            let x = event.clientX
            let y = event.clientY
            WindowLoad.mouse_x = x
            WindowLoad.mouse_y = y
            HoverCard.onMouseMove(x, y, 1, 1)
        }
        window.onmousedown = (event) => {
            if (event.button == 1 || event.buttons == 4) {
                HoverCard.rotate(+1)
                event.preventDefault();
            }
        }
        window.onblur = function(event) {
            UI.hold_ctrl = false
            UI.hold_alt = false
            UI.updateAnimeTime()
            document.body.classList.remove('hold-alt')
            document.querySelector("#skipping-icon")!.classList.add('hide')
        }
        window.onkeydown = function(event) {
            WindowLoad.onKeyDown(event)
        }
        window.onkeyup = function(event) {
            WindowLoad.onKeyUp(event)
        }
        window.onclick = function(event) {
            WindowLoad.onClick(event)
        }
    }
}

export class SwipeDetector {
    static touchStartX = 0;
    static touchEndX = 0;

    static div = document.getElementById('right-side-bar') as HTMLElement

    static handleTouchStart(event: TouchEvent) {
        SwipeDetector.touchStartX = event.changedTouches[0].screenX;
    }

    static handleTouchEnd(event: TouchEvent) {
        SwipeDetector.touchEndX = event.changedTouches[0].screenX;
        SwipeDetector.handleGesture();
    }

    static handleGesture() {
        if (SwipeDetector.touchEndX < SwipeDetector.touchStartX) {
            console.log('Swiped left');
            SwipeDetector.div.classList.add('clicked')
        }
        if (SwipeDetector.touchEndX > SwipeDetector.touchStartX) {
            console.log('Swiped right');
            SwipeDetector.div.classList.remove('clicked')
        }
    }

    static attachSwipeListeners() {
        const element = document.querySelector('body') as HTMLElement
        element.addEventListener('touchstart', SwipeDetector.handleTouchStart, false);
        element.addEventListener('touchend', SwipeDetector.handleTouchEnd, false);
    }
}
