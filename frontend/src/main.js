import { createApp } from 'vue';
import { router } from '@/router';
import ApiPlugin from "@/plugins/api";
import AlertPlugin from "@/plugins/alert";
import App from "@/App.vue";

const app = createApp(App).use(router).use(AlertPlugin).use(ApiPlugin);
app.config.unwrapInjectedRef = true;
app.mount('#app');
