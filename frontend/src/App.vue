<template>
  <el-container class="layout-container">
    <el-header class="layout-header">
      <div class="header-left">
        <div class="logo">
          <el-icon :size="28"><DataAnalysis /></el-icon>
          <span class="logo-text">Lakehouse Sync Dashboard</span>
        </div>
      </div>
      <div class="header-right">
        <el-tag type="info" effect="dark">v1.0.0</el-tag>
        <el-divider direction="vertical" />
        <span class="user-info">
          <el-icon><User /></el-icon>
          Admin
        </span>
      </div>
    </el-header>
    <el-container>
      <el-aside width="220px" class="layout-aside">
        <el-menu
          :default-active="activeMenu"
          class="layout-menu"
          background-color="transparent"
          text-color="#b8c5d1"
          active-text-color="#00d4ff"
          router
        >
          <el-menu-item index="/dashboard">
            <el-icon><Monitor /></el-icon>
            <span>总览大屏</span>
          </el-menu-item>
          <el-menu-item index="/acceleration-network">
            <el-icon><Connection /></el-icon>
            <span>加速网络</span>
          </el-menu-item>
          <el-menu-item index="/dictionary">
            <el-icon><Collection /></el-icon>
            <span>数据字典</span>
          </el-menu-item>
          <el-menu-item index="/storage-tree">
            <el-icon><FolderOpened /></el-icon>
            <span>存储下钻分析</span>
          </el-menu-item>
          <el-menu-item index="/trend">
            <el-icon><TrendCharts /></el-icon>
            <span>趋势分析</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style lang="scss" scoped>
.layout-container {
  height: 100vh;
  background: $bg-primary;
}

.layout-header {
  height: 64px;
  background: linear-gradient(90deg, $bg-header-start 0%, $bg-header-end 100%);
  border-bottom: 1px solid $border-color;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);

  .header-left {
    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      color: $color-primary;

      .logo-text {
        font-size: 20px;
        font-weight: 600;
        letter-spacing: 1px;
        background: linear-gradient(90deg, $color-primary 0%, $color-accent 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    color: $text-secondary;

    .user-info {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 14px;
    }
  }
}

.layout-aside {
  background: $bg-secondary;
  border-right: 1px solid $border-color;
}

.layout-menu {
  border-right: none;
  padding-top: 16px;

  .el-menu-item {
    height: 52px;
    line-height: 52px;
    margin: 4px 12px;
    border-radius: 8px;
    transition: all 0.3s ease;

    &:hover {
      background: rgba(0, 212, 255, 0.08) !important;
      color: $color-primary !important;
    }

    &.is-active {
      background: rgba(0, 212, 255, 0.15) !important;
      box-shadow: inset 3px 0 0 $color-primary;
    }
  }
}

.layout-main {
  background: $bg-primary;
  padding: 20px;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
