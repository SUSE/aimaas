import { alertStore } from "../composables/alert";

export default {
    install: (app) => {
        app.config.globalProperties.$alerts = alertStore;
    }
}
