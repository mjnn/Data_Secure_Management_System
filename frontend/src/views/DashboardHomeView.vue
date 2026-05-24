<template>
  <section
    class="dashboard-blank dsms-glass-panel dsms-animate-stagger-0"
    aria-label="首页内容"
  >
    <h2 class="dashboard-blank__title dsms-animate-stagger-1">欢迎使用数据安全治理工作台</h2>
    <p class="dashboard-blank__desc dsms-animate-stagger-2">
      尚未配置任何功能模块。后续将按需在左侧导航中接入业务页面。
    </p>
  </section>
</template>

<style scoped>
.dashboard-blank {
  padding: 36px 40px;
}

.dashboard-blank__title {
  margin: 0 0 16px;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--dsms-text);
}

.dashboard-blank__desc {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--dsms-text-secondary);
}
</style>
