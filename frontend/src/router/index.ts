import { createRouter, createWebHistory } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/routines' },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { publicOnly: true },
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: () => import('../views/AuthCallbackView.vue'),
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('../views/UsersView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/routines',
      name: 'routines',
      component: () => import('../views/RoutinesView.vue'),
    },
    {
      path: '/routines/:id',
      name: 'routine-detail',
      component: () => import('../views/RoutineDetailView.vue'),
      props: (route) => ({ id: Number(route.params.id) }),
      beforeEnter: (to) => {
        if (isNaN(Number(to.params.id))) {
          console.warn('Invalid route: id is not a number:', to.params.id)
          return { name: 'routines' }
        }
      },
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/ExecutionHistoryView.vue'),
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  const { isAuthenticated } = storeToRefs(authStore)

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.publicOnly && isAuthenticated.value) {
    return { name: 'routines' }
  }

  return true
})

export default router
