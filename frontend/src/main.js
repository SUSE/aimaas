import { createApp } from 'vue';
import { router } from '@/router';
import {API} from "@/api";
import {AlertStore} from "@/alert";
import App from "@/App";

const app = createApp(App).use(router);
app.config.unwrapInjectedRef = true;
app.config.globalProperties.$alerts = new AlertStore();
app.config.globalProperties.$api =  new API(process.env.VUE_APP_API_BASE);
app.mount('#app');
