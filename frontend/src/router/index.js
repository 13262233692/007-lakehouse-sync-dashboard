import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '总览大屏' }
  },
  {
    path: '/dictionary',
    name: 'Dictionary',
    component: () => import('@/views/Dictionary.vue'),
    meta: { title: '数据字典' }
  },
  {
    path: '/storage-tree',
    name: 'StorageTree',
    component: () => import('@/views/StorageTree.vue'),
    meta: { title: '存储下钻分析' }
  },
  {
    path: '/trend',
    name: 'Trend',
    component: () => import('@/views/Trend.vue'),
    meta: { title: '趋势分析' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - Lakehouse Sync Dashboard`
  }
  next()
})

export default router
