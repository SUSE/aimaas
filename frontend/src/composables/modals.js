import {randomUUID} from "@/utils";


export class Button {
    constructor({icon, text, css}) {
        this.id = randomUUID();
        this.icon = icon;
        this.text = text;
        this.css = css;
    }
}


export class ModalButton extends Button {
    constructor({callback, icon, text, css}) {
        super({icon: icon, text: text, css: css});
        if (!(callback instanceof Function)) {
            throw new TypeError("Callback must be a function");
        }
        this.callback = callback;
    }
}
