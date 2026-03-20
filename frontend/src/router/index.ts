import { createRouter, createWebHistory } from 'vue-router'
import SequenceListView from '../views/SequenceListView.vue'
import SequenceDetailView from '../views/SequenceDetailView.vue'
import LoginView from '../views/LoginView.vue'
import AuthCallbackView from '../views/AuthCallbackView.vue'
import UsersView from '../views/UsersView.vue'

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
  ],
})

export default router
