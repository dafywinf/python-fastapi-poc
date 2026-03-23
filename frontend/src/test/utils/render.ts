import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import type { Component } from 'vue'
import type { Router } from 'vue-router'
import { createMemoryHistory, createRouter } from 'vue-router'
import { primevuePt } from '../../primevue-pt'

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
}

export async function mountWithApp(
  component: Component,
  options: Parameters<typeof mount>[1] = {},
  currentPath = '/',
) {
  const queryClient = createTestQueryClient()
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
      { path: '/users', component: { template: '<div />' } },
      { path: '/routines', component: { template: '<div />' } },
      { path: '/routines/:id', component: { template: '<div />' } },
      { path: '/history', component: { template: '<div />' } },
    ],
  })

  await router.push(currentPath)
  await router.isReady()

  return mount(component, {
    ...options,
    global: {
      ...options.global,
      plugins: [
        createPinia(),
        router,
        [VueQueryPlugin, { queryClient }],
        [PrimeVue, { unstyled: true, pt: primevuePt }],
        ToastService,
        ...(options.global?.plugins ?? []),
      ],
    },
  })
}

export type { Router }
