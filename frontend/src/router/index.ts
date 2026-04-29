import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('../views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
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
      meta: { requiresAuth: true },
    },
    {
      path: '/routines/new',
      name: 'routine-create',
      component: () => import('../views/RoutineFormView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/routines/:id',
      name: 'routine-detail',
      component: () => import('../views/RoutineDetailView.vue'),
      props: (route) => ({ id: Number(route.params.id) }),
      meta: { requiresAuth: true },
      beforeEnter: (to) => {
        if (isNaN(Number(to.params.id))) {
          console.warn('Invalid route: id is not a number:', to.params.id)
          return { name: 'routines' }
        }
      },
    },
    {
      path: '/routines/:id/edit',
      name: 'routine-edit',
      component: () => import('../views/RoutineFormView.vue'),
      props: (route) => ({ id: Number(route.params.id) }),
      meta: { requiresAuth: true },
      beforeEnter: (to) => {
        if (isNaN(Number(to.params.id))) {
          console.warn('Invalid route: id is not a number:', to.params.id)
          return { name: 'routines' }
        }
      },
    },
    {
      path: '/executing',
      redirect: '/',
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/ExecutionHistoryView.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const { isAuthenticated, checkAuth } = useAuth()

  await checkAuth()

  if (to.meta.requiresAuth && !isAuthenticated.value) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.publicOnly && isAuthenticated.value) {
    return { name: 'dashboard' }
  }

  return true
})

export default router
