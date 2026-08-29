import { Setting } from './settings.js'
// @ts-ignore
import { Notifications } from '../lib/notifications.js'
import { withCardImageRevision } from '../card_image_url.js'

export class Notify {

    static notis = new Notifications(document.querySelector(".notifications"));

    static {
        const logo_code = [
            'KeyI', 'KeyR', 'KeyE', 'KeyF',
            'KeyR', 'KeyI', 'KeyX', 'KeyS',
        ];

        let logo_index = 0;
        let logo_code_string = ""

        document.addEventListener('keydown', (event) => {
            if (event.code === logo_code[logo_index]) {
                logo_index++;
                logo_code_string += event.key
                if (logo_index === logo_code.length) {
                    Notify.create("", "", `${logo_code_string.charAt(0).toUpperCase() + logo_code_string.slice(1)} (c)`)
                    logo_index = 0;
                    logo_code_string = ""
                }
            } else {
                logo_index = 0;
                logo_code_string = ""
            }
        });
    }

    static showResponse(text: string) {
        Notify.create("RESPONSE", "debug", text, 2)
    }

    static showAchievement(text: string) {
        if( !Setting.show_achievement ) {
            return
        }
        let div = document.querySelector('#achievement-bar') as HTMLElement
        div.classList.remove('remove')
        div.classList.add('enter')
        div.innerHTML = text
        setTimeout(() => {
            div.classList.remove('enter')
            div.classList.add('remove')
        }, 2000);
    }

    static pause() {
        Notify.notis.pause()
    }

    static unpause() {
        Notify.notis.unpause()
    }

    static create(
        title = "",
        ex_class_name = "",
        description = "",
        duration = 4,
        destroyOnClick = true,
        clickFunction = undefined,
    ) {
        Notify.notis.create(
            title,
            ex_class_name,
            description,
            duration,
            destroyOnClick,
            clickFunction
        );
    }

    static showStatisticsText(text: string) {
        if( !Setting.is_debug && Setting.statistics_off ) {
            return
        }

        let class_name = 'statistics'
        let div_test = `<span class='${class_name}'>${text}</span>`
        Notify.create("STATISTIC", "", div_test)
    }

    static showStatistics(card_id: string, text: string, count: number) {
        if( !Setting.is_debug && Setting.statistics_first && count != 1 ) {
            return
        }
        if( ["PutIntoPlay", "Attached", "Hero"].includes(text)  ) {
            text = "Enters Play"
        }
        // if( ["Discard"].includes(text)  ) {
        //     text = "Defeated"
        // }

        const image_url = withCardImageRevision(card_id)
        let notify_text = `<img class='statistics-notify-img' style='--bg-image-true: url("${image_url}")'></img>  ${text} x${count}`

        Notify.showStatisticsText(notify_text)
    }

    static showCommand(text: string) {
        Notify.create("COMMAND", "", text, 2)
    }
}
