<template>
  <el-button
    circle
    text
    type="primary"
    class="dsms-theme-toggle"
    :aria-pressed="isDark ? 'true' : 'false'"
    :aria-label="isDark ? '切换为浅色模式' : '切换为深色模式'"
    :title="isDark ? '浅色模式' : '深色模式'"
    @click="toggleTheme"
  >
    <el-icon :size="18">
      <Sunny v-if="isDark" />
      <Moon v-else />
    </el-icon>
  </el-button>
</template>

<script setup>
import { Moon, Sunny } from "@element-plus/icons-vue";
import { useDsmsTheme } from "../composables/useDsmsTheme";

const { isDark, toggleTheme } = useDsmsTheme();
</script>

<style scoped>
.dsms-theme-toggle {
  color: var(--dsms-text-secondary);
  flex-shrink: 0;
  transition:
    color var(--dsms-duration-short) var(--dsms-ease-standard),
    background-color var(--dsms-duration-short) var(--dsms-ease-standard);
}

.dsms-theme-toggle:hover {
  color: var(--dsms-text);
  background: rgba(128, 128, 128, 0.12) !important;
}

@media (prefers-reduced-motion: reduce) {
  .dsms-theme-toggle {
    transition: none;
  }
}
</style>
