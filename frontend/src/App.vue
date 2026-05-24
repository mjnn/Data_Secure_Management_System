<template>
  <router-view v-slot="{ Component, route }">
    <transition name="dsms-route" mode="out-in">
      <!-- 嵌套路由下子页切换不应卸载控制台壳，仅登录与业务壳互切时换 key -->
      <component
        :is="Component"
        :key="route.path === '/login' ? 'login' : 'dashboard-shell'"
      />
    </transition>
  </router-view>
</template>
