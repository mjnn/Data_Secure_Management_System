import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";
import "./styles/portal-theme.css";

import { initDsmsThemeBeforeMount } from "./composables/useDsmsTheme";
import App from "./App.vue";
import router from "./router";

initDsmsThemeBeforeMount();

createApp(App).use(router).use(ElementPlus).mount("#app");
