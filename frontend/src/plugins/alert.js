import {randomUUID} from "@/utils";


const ALERT_LEVELS = [
    'primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark', 'cta'
];

class AlertMessage {
    constructor(level, msg) {
        if (!ALERT_LEVELS.includes(level)){
            throw new TypeError("Invalid alert level.");
        }
        this.level = level;
        this.message = msg;
        this.id = `alert-${randomUUID()}`;
    }
}

class AlertStore {
    constructor() {
        this.storage = {}
    }

    clear() {
        for (const key in this.storage) {
            delete this.storage[key];
        }
    }

    push(level, msg) {
        const alert = new AlertMessage(level, msg);
        this.storage[alert.id] = alert;
    }

    pop(alertId) {
        delete this.storage[alertId];
    }

    get values() {
        return Object.values(this.storage);
    }
}

export default {
    install: (app) => {
        app.config.globalProperties.$alerts = new AlertStore();
    }
}