import { createApp } from 'vue';
import { router } from '@/router';
import {API} from "@/api";
import AlertPlugin from "@/plugins/alert";
import App from "@/App";

const app = createApp(App).use(router).use(AlertPlugin);
app.config.unwrapInjectedRef = true;
app.config.globalProperties.$api =  new API(process.env.VUE_APP_API_BASE);
app.mount('#app');
