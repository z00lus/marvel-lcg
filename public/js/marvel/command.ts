import { Cards } from "./cards.js";
import { Notify } from "./notify.js";

export class Command {

    private static newWindow: Window|null = null

    static setLastClickCard(card_div: HTMLElement) {
        if( Command.newWindow && !Command.newWindow.closed ) {
            const card = Cards.getCard(Number(card_div.dataset.id!))!
            const data = {
                type: 'setLastClickCard',
                card_object_id: card_div.dataset.id,
                card_id: card.card_id,
                card_name: card.name,
            };
            Command.newWindow.postMessage(data, '*')
            Command.newWindow.focus();
            return true
        }
        else {
            return false
        }
    }

    static async saveLocal(): Promise<string> {
        const response = await fetch("save_local", { method: "POST" });
        const data = await response.json();
        if( !response.ok ) {
            const error = data.error || `Replay save failed: ${response.status}`
            Notify.showCommand(error)
            throw new Error(error)
        }

        const path = data.path || data.file
        Notify.showCommand(`Replay saved: ${path}`)
        return path
    }

    static async uploadSave(save_type: "Bug"|"Crash"|"Share", comment: string="") {
        if( Command.newWindow && !Command.newWindow.closed ) {
            Command.newWindow.close()
        }
        // window.open(`report.html?save_type=${save_type}`, "newWindow", "width=400,height=320");
        // Open the new window
        Command.newWindow = window.open(`report`, "newWindow", "width=400,height=320")!;

        const data = {
            type: 'uploadSave',
            save_type: save_type,
            comment: comment
        };

        // Send data to the new window once it has loaded
        Command.newWindow.onload = () => {
            Command.newWindow!.postMessage(data, '*'); // Use '*' to allow any origin or specify the target origin
        };
    }
}
