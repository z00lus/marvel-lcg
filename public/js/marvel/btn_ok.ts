import { Effect } from "./effect.js";
import { SelectStep } from "./select.js";
import { UI } from "./ui.js";

export class BtnOk
{
    static response_interrupt_class_name = "response_interrupt"

    static btn_end_div  = document.getElementById('btn-end') as HTMLButtonElement;
    static btn_ok_div   = document.getElementById('btn-ok') as HTMLButtonElement;

    static refreshTime(time_out: number) {
        BtnOk.btn_end_div.dataset.time = time_out.toString()
    }

    static tryRemoveResponseInterruptClass() {
        if( Effect.response_json_ask ) {
            if( !Effect.is_ex_effect ) {
                BtnOk.btn_end_div.classList.remove(BtnOk.response_interrupt_class_name)
                BtnOk.btn_end_div.classList.remove("ex_effect")
        }
        }
        return true
    }

    static clean() {
        BtnOk.btn_end_div.classList.remove(BtnOk.response_interrupt_class_name)
        BtnOk.btn_end_div.classList.remove("ex_effect")
    }

    static setDisable(disable: boolean) {
        BtnOk.btn_end_div.disabled = disable
        BtnOk.btn_ok_div.disabled = true
        if( disable ) {
            BtnOk.tryRemoveResponseInterruptClass()
        }
        // CardEffect.is_in_event = ''
    }
    static setOk(text: string) {
        BtnOk.btn_ok_div.classList.remove("overpay")

        if( text == "OverPay" ) {
            BtnOk.btn_ok_div.innerHTML = "Over<br/>Pay"
            BtnOk.btn_ok_div.classList.add('overpay')
            BtnOk.btn_ok_div.classList.add('ok')
            BtnOk.btn_ok_div.disabled = false
        }
        else if( text ) {
            BtnOk.btn_ok_div.innerHTML = "OK"
            BtnOk.btn_ok_div.classList.add('ok')
            BtnOk.btn_ok_div.disabled = false
        }
    }
    static enableCancelButton()
    {
        // if( Effect.response_json_ask.event_name == "WhenPlayerChooseAbility" ) {
        if( Effect.is_ex_effect ) {
            const text = "Cancel"
            BtnOk.btn_end_div.classList.add("ex_effect")
            BtnOk.btn_end_div.classList.add(BtnOk.response_interrupt_class_name)
            BtnOk.btn_end_div.innerHTML = text
        }
    }
    static setCancel(text: string)
    {
        BtnOk.btn_end_div.classList.remove("action")
        BtnOk.btn_end_div.classList.remove("forced_action")
        BtnOk.btn_end_div.classList.remove("defense")

        if( Effect.is_in_event == 'response' ||
            Effect.is_in_event == 'interrupt' ||
            Effect.is_in_event == 'asking'
        ) {
            BtnOk.btn_end_div.classList.add(BtnOk.response_interrupt_class_name)
            BtnOk.btn_end_div.classList.remove("ex_effect")
        } else {
            BtnOk.tryRemoveResponseInterruptClass()
        }

        if( Effect.is_in_event == 'response' ) {
            if( !Effect.show_cancel ){
                BtnOk.btn_end_div.classList.add("forced_action")
            }
            text = 'End<br/>Response'
        }
        else
        if( Effect.is_in_event == 'interrupt' ) {
            if( !Effect.show_cancel ){
                BtnOk.btn_end_div.classList.add("forced_action")
            }
            text = 'Continue'
        }
        else
        if( Effect.is_in_event == 'asking' ) {
            if( !Effect.show_cancel ){
                BtnOk.btn_end_div.classList.add("forced_action")
            }
            text = 'Continue'
        }
        else
        if( SelectStep.isCost() ) {
            text = 'Cancel<br/>Pay'
        }
        else
        if( SelectStep.isTargets() ) {
            text = 'Cancel'
        }
        else
        if( UI.event_name == 'WhenUnitBeingAttack' ) {
            text = 'End<br/>Defense'
            BtnOk.btn_end_div.classList.add("defense")
        }
        else
        if( Effect.is_in_event == 'in_turn' ) {
            if( !Effect.show_cancel ){
                BtnOk.btn_end_div.classList.add("forced_action")
            }
            else
            if( SelectStep.isCard() ) {
                text = 'End<br/>Turn'
                BtnOk.btn_end_div.classList.add("action")
            } else {
                text = 'Cancel'
            }
        }

        BtnOk.btn_ok_div.disabled = true
        BtnOk.btn_end_div.innerHTML = text
    }
}
