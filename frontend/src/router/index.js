import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
  },
  {
    path: '/training',
    name: 'training',
    component: () => import('../views/TrainingView.vue'),
  },
  {
    path: '/training/:taskId/result',
    name: 'training-result',
    component: () => import('../views/TrainingResultView.vue'),
    props: true,
  },
  {
    path: '/history',
    name: 'history',
    component: () => import('../views/LearningHistoryView.vue'),
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../views/ProfileView.vue'),
  },
  {
    path: '/sidequest',
    name: 'sidequest',
    component: () => import('../views/SidequestView.vue'),
  },
  {
    path: '/isolated-test',
    name: 'isolated-test',
    component: () => import('../views/IsolatedTestView.vue'),
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
