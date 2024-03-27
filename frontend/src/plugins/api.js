import { reactive } from "vue";
import { api } from "../composables/api";

export default {
    install: (app) => {
        app.config.globalProperties.$api = reactive(api);
    }
}
