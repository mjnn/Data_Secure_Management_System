import { ref } from "vue";

const STORAGE_KEY = "dsms_portal_color_scheme";

/** 与顶栏切换、localStorage、`html.dark` 同步 */
const isDark = ref(false);

function readStoredMode() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "dark" || v === "light") return v;
  } catch (_e) {
    /* ignore */
  }
  return "light";
}

/** 须在 `createApp` 之前调用，避免首屏闪浅色 */
export function initDsmsThemeBeforeMount() {
  if (typeof document === "undefined") return;
  const mode = readStoredMode();
  const dark = mode === "dark";
  document.documentElement.classList.toggle("dark", dark);
  document.documentElement.setAttribute("data-dsms-theme", mode);
  isDark.value = dark;
}

export function useDsmsTheme() {
  function applyTheme(mode) {
    if (typeof document === "undefined") return;
    const dark = mode === "dark";
    document.documentElement.classList.toggle("dark", dark);
    document.documentElement.setAttribute("data-dsms-theme", mode);
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch (_e) {
      /* ignore */
    }
    isDark.value = dark;
  }

  function toggleTheme() {
    applyTheme(isDark.value ? "light" : "dark");
  }

  return { isDark, toggleTheme, applyTheme };
}
