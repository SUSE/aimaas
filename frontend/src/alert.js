export const ALERT_LEVELS = [
    'primary', 'secondary', 'success', 'danger', 'warning', 'info', 'light', 'dark', 'cta'
];

export class AlertMessage {
    constructor(level, msg) {
        if (!ALERT_LEVELS.includes(level)){
            throw new TypeError("Invalid alert level.");
        }
        this.level = level;
        this.message = msg;
        this.id = `alert-${crypto.randomUUID()}`;
    }
}

export class AlertStore {
    constructor() {
        this.storage = {}
    }

    clear() {
        for (const key in this.storage) {
            delete this.storage[key];
        }
    }

    push(alert) {
        if (!(alert instanceof AlertMessage)) {
            throw new TypeError("Only instances of AlertMessage are allowed");
        }

        this.storage[alert.id] = alert;
    }

    pop(alert) {
        if (alert instanceof AlertMessage) {
            delete this.storage[alert.id];
        }
        else if (alert instanceof String) {
            delete this.storage[alert];
        }
    }

    get values() {
        return Object.values(this.storage);
    }
}