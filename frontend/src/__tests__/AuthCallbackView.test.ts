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

// Track replaceState calls to verify the fragment is cleared
const replaceStateSpy = vi.spyOn(window.history, 'replaceState')

describe('AuthCallbackView', () => {
  beforeEach(() => {
    localStorageMock.clear()
    replaceStateSpy.mockClear()
    vi.resetModules()
  })

  it('stores token from URL fragment in localStorage and navigates to /', async () => {
    // Simulate the browser having a fragment set by the OAuth callback redirect
    Object.defineProperty(window, 'location', {
      value: { ...window.location, hash: '#token=test-jwt-token', pathname: '/auth/callback' },
      writable: true,
    })

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

    expect(localStorageMock.getItem('access_token')).toBe('test-jwt-token')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('clears the URL fragment from history after extracting the token', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, hash: '#token=test-jwt-token', pathname: '/auth/callback' },
      writable: true,
    })

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

    expect(replaceStateSpy).toHaveBeenCalledWith(null, '', '/auth/callback')
  })

  it('navigates to / even when no token is present', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, hash: '', pathname: '/auth/callback' },
      writable: true,
    })

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

    expect(localStorageMock.getItem('access_token')).toBeNull()
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('does not store a token when fragment contains an empty token value', async () => {
    Object.defineProperty(window, 'location', {
      value: { ...window.location, hash: '#token=', pathname: '/auth/callback' },
      writable: true,
    })

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

    expect(localStorageMock.getItem('access_token')).toBeNull()
    expect(router.currentRoute.value.path).toBe('/')
  })
})
