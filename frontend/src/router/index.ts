import { createRouter, createWebHistory } from 'vue-router'
import SequenceListView from '../views/SequenceListView.vue'
import SequenceDetailView from '../views/SequenceDetailView.vue'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'
import UsersView from '../views/UsersView.vue'
import RoutinesView from '../views/RoutinesView.vue'
import RoutineDetailView from '../views/RoutineDetailView.vue'
import ExecutionHistoryView from '../views/ExecutionHistoryView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/sequences',
    },
    {
      path: '/sequences',
      name: 'sequences',
      component: SequenceListView,
    },
    {
      path: '/sequences/:id',
      name: 'sequence-detail',
      component: SequenceDetailView,
      props: (route) => ({ id: Number(route.params.id) }),
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/auth/callback',
      name: 'auth-callback',
      component: AuthCallbackView,
    },
    {
      path: '/users',
      name: 'users',
      component: UsersView,
    },
    { path: '/routines', name: 'routines', component: RoutinesView },
    {
      path: '/routines/:id',
      name: 'routine-detail',
      component: RoutineDetailView,
      props: (route) => ({ id: Number(route.params.id) }),
    },
    { path: '/history', name: 'history', component: ExecutionHistoryView },
  ],
})

export default router
