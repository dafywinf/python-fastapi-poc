import { beforeMount } from '@playwright/experimental-ct-vue/hooks'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { createMemoryHistory, createRouter } from 'vue-router'
import { primevuePt } from '../src/primevue-pt'

beforeMount(async ({ app }) => {
  // Pinia — required for composables that use a store
  app.use(createPinia())

  // Stub router — CT components must not navigate. A memory router with a
  // catch-all prevents "No match found" console warnings from any component
  // that transitively imports useRouter() (e.g. via useAuth).
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  })
  app.use(router)
  await router.isReady()

  // TanStack Query — required by any component using useQuery or useMutation
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  app.use(VueQueryPlugin, { queryClient })

  // PrimeVue — unstyled + pass-through config must match production exactly so
  // component structure (and therefore locators) are identical to the live app
  app.use(PrimeVue, { unstyled: true, pt: primevuePt })
  app.use(ToastService)
})
