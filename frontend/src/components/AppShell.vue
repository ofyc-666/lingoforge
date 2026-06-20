<script setup>
import SidebarNav from './SidebarNav.vue'
import TopBar from './TopBar.vue'
</script>

<template>
  <div class="app-shell">
    <TopBar />
    <div class="app-body">
      <SidebarNav />
      <main class="app-content">
        <router-view v-slot="{ Component, route }">
          <transition name="fade" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  background: var(--color-bg);
}

.app-body {
  display: flex;
  padding-top: var(--topbar-height);
  min-height: 100vh;
}

.app-content {
  flex: 1;
  margin-left: var(--sidebar-width);
  padding: 28px 32px;
  min-width: 0;
}

@media (max-width: 900px) {
  .app-content {
    margin-left: 0;
    padding: 20px 16px;
  }
}
</style>
