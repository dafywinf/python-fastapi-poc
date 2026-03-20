import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRouter, createMemoryHistory } from 'vue-router'
import AuthCallbackView from '../views/AuthCallbackView.vue'

const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(global, 'localStorage', { value: localStorageMock })

describe('AuthCallbackView', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.resetModules()
  })

  it('stores token from URL in localStorage and navigates to /', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback?token=test-jwt-token')

    mount(AuthCallbackView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(localStorageMock.getItem('access_token')).toBe('test-jwt-token')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('navigates to / even when no token is present', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback')

    mount(AuthCallbackView, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/')
  })
})
