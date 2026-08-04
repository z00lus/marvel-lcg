import { ButtonSetting, Setting } from './settings.js'
import { Effect } from './effect.js'
import { Button } from './buttons.js'
import { SelectStep } from './select.js'
import { BtnOk } from './btn_ok.js'
import { Cards } from './cards.js'
import { Game } from './game.js'

export class Replay {
    static prepared_replay = false
    static preparing_replay = false

    private static controls: HTMLElement|null = null
    private static playButton: HTMLButtonElement|null = null
    private static progress: HTMLInputElement|null = null
    private static stepCounter: HTMLOutputElement|null = null
    private static navigationTarget: number|null = null
    private static maxStep = 0

    static initialize() {
        if( !Setting.replay_mode ) {
            return
        }

        document.body.classList.add('replay-mode')
        Replay.controls = document.getElementById('replay-controls')
        Replay.playButton = document.getElementById('replay-play-pause') as HTMLButtonElement
        Replay.progress = document.getElementById('replay-progress') as HTMLInputElement
        Replay.stepCounter = document.getElementById('replay-step-counter') as HTMLOutputElement

        document.getElementById('replay-first')?.addEventListener('click', () => Replay.goToStep(0))
        document.getElementById('replay-previous')?.addEventListener('click', () => Replay.stepBackward())
        Replay.playButton?.addEventListener('click', () => Replay.togglePlaying())
        document.getElementById('replay-next')?.addEventListener('click', () => Replay.stepForward())
        document.getElementById('replay-last')?.addEventListener('click', () => Replay.goToStep(Replay.maxStep))

        Replay.progress?.addEventListener('input', () => {
            if( Replay.stepCounter && Replay.progress ) {
                Replay.stepCounter.value = `${Replay.progress.value} / ${Replay.maxStep}`
            }
        })
        Replay.progress?.addEventListener('change', () => {
            if( Replay.progress ) {
                Replay.goToStep(Number(Replay.progress.value))
            }
        })

        Replay.setPlaying(Boolean(ButtonSetting.is_replay))
        Replay.updateControls(0, 0)
    }

    static setPlaying(playing: boolean) {
        if( !Setting.replay_mode ) {
            return
        }

        if( playing && Game.current_step_id >= Replay.maxStep && Replay.maxStep > 0 ) {
            playing = false
        }

        ButtonSetting.is_replay = Number(playing)
        document.body.classList.toggle('replaying', playing)

        const oldReplayButton = document.getElementById('replay-btn')
        oldReplayButton?.classList.toggle('clicked', playing)

        if( Replay.playButton ) {
            Replay.playButton.innerHTML = playing
                ? '<i class="fa fa-pause" aria-hidden="true"></i>'
                : '<i class="fa fa-play" aria-hidden="true"></i>'
            Replay.playButton.title = playing ? 'Pause replay' : 'Play replay'
            Replay.playButton.setAttribute('aria-label', Replay.playButton.title)
        }

        if( playing && Game.asking_players.length > 0 ) {
            Replay.doReplay()
        }
    }

    static togglePlaying() {
        Replay.setPlaying(!Boolean(ButtonSetting.is_replay))
    }

    static updateControls(currentStep: number, maxStep: number) {
        if( !Setting.replay_mode ) {
            return
        }

        Replay.maxStep = Math.max(0, maxStep)
        if( Replay.navigationTarget === currentStep ) {
            Replay.navigationTarget = null
        }

        if( Replay.progress ) {
            Replay.progress.max = Replay.maxStep.toString()
            Replay.progress.value = Math.min(currentStep, Replay.maxStep).toString()
        }
        if( Replay.stepCounter ) {
            Replay.stepCounter.value = `${currentStep} / ${Replay.maxStep}`
        }

        const navigating = Replay.navigationTarget !== null
        const firstButton = document.getElementById('replay-first') as HTMLButtonElement|null
        const previousButton = document.getElementById('replay-previous') as HTMLButtonElement|null
        const nextButton = document.getElementById('replay-next') as HTMLButtonElement|null
        const lastButton = document.getElementById('replay-last') as HTMLButtonElement|null

        if( firstButton ) firstButton.disabled = navigating || currentStep <= 0
        if( previousButton ) previousButton.disabled = navigating || currentStep <= 0
        if( nextButton ) nextButton.disabled = navigating || currentStep >= Replay.maxStep
        if( lastButton ) lastButton.disabled = navigating || currentStep >= Replay.maxStep
        if( Replay.progress ) Replay.progress.disabled = navigating || Replay.maxStep <= 0
        if( Replay.playButton ) Replay.playButton.disabled = navigating || Replay.maxStep <= 0 || currentStep >= Replay.maxStep

        Replay.controls?.classList.toggle('seeking', navigating)

        if( currentStep >= Replay.maxStep && Replay.maxStep > 0 ) {
            Replay.setPlaying(false)
        }
    }

    static goToStep(targetStep: number) {
        if( !Setting.replay_mode || Replay.navigationTarget !== null ) {
            return
        }

        const target = Math.max(0, Math.min(targetStep, Replay.maxStep))
        if( target == Game.current_step_id ) {
            return
        }

        Replay.setPlaying(false)
        Replay.navigationTarget = target
        Replay.updateControls(Game.current_step_id, Replay.maxStep)
        Button.doDebug(`/replay_goto ${target}`, false)
    }

    static stepBackward() {
        Replay.goToStep(Game.current_step_id - 1)
    }

    static stepForward() {
        Replay.goToStep(Game.current_step_id + 1)
    }

    static doReplay(temp=false, delay=300, do_skip=false) {
        if( Replay.prepared_replay || Replay.preparing_replay ) {
            return false
        }
        if( Effect.response_json_ask.replay_input == '{}' ) {
            return false
        }

        const completeOperation = Boolean(ButtonSetting.is_replay || temp)
        Replay.preparing_replay = true
        setTimeout(async () => {
            let data = JSON.parse(Effect.response_json_ask.replay_input)
            let is_debug_command = false
            function sleep(ms: number) {
                return new Promise(resolve => setTimeout(resolve, ms));
            }

            if( data['id'].startsWith(":") ) {
                is_debug_command = true
            }
            else if( data['id'] != '' ) {
                const object_id = Number(data['id'].match(/c(\d+) /)[1])
                const card_div = Cards.getDiv(object_id)!

                if( SelectStep.isCard() ) {
                    await sleep(delay);
                    Effect.onCardClick(card_div, false, true)
                }

                if( SelectStep.isEffect() ) {
                    await sleep(delay);
                    const str = data['id'].match(/e(\d+) (.*) c(\d+)/)[2].replaceAll(" ", "_")
                    let buttons = Effect.options_button_div.querySelectorAll('button')
                    if( str == "Cancel" ) {
                        Effect.onCancel()
                    }
                    else if( buttons.length == 1 ) {
                        buttons[0].click()
                    }
                    else {
                        for( let e of buttons ) {
                            const button_text = JSON.parse(e.dataset.json_str!)['name']
                            if( str == button_text) {
                                e.click()
                                break
                            }
                        }
                    }
                }

                if( !SelectStep.isTargets() && !SelectStep.isCost() ) {
                    if( !SelectStep.isCard() ) {
                        Button.doPost(false)
                    }
                }
                if( SelectStep.isTargets() && data['targets'].length > 0 ) {
                    await sleep(delay);
                    for( let res of data['targets'] ) {
                        const object_id = Number(res.match(/c(\d+) /)[1])
                        const card_div = Cards.getDiv(object_id)!
                        Effect.onCardClick(card_div, false, true)
                    }
                }

                if( !SelectStep.isCost() ) {
                    if( BtnOk.btn_end_div.classList.contains('ok') ||
                        !BtnOk.btn_ok_div.disabled ) {
                        Button.doPost(false)
                    }
                }
                if( SelectStep.isCost() && data['resources'].length > 0 ) {
                    await sleep(delay);
                    for( let res of data['resources'] ) {
                        const object_id = Number(res.match(/c(\d+) /)[1])
                        const card_div = Cards.getDiv(object_id)!
                        Effect.onCardClick(card_div, false, true)
                    }
                }
            }
            Replay.prepared_replay = true
            Replay.preparing_replay = false

            if( completeOperation ) {
                setTimeout(() => {
                    document.querySelectorAll('.deck.clicked').forEach( deck_div => {
                        deck_div.classList.remove('clicked')
                    })
                    if( is_debug_command ) {
                        Button.doNext()
                    }
                    else if( SelectStep.isCost() ) {
                        Button.doPost(true)
                    } else {
                        Button.doCancel()
                    }
                    if( do_skip ) {
                        Button.doToEnd()
                    }
                }, delay);
            }
        }, 100);
        return true
    }
}
