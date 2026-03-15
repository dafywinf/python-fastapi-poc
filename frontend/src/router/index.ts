import { createRouter, createWebHistory } from 'vue-router'
import SequenceListView from '../views/SequenceListView.vue'
import SequenceDetailView from '../views/SequenceDetailView.vue'

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
  ],
})

export default router
