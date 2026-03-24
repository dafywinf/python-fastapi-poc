import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { applyFrontendAllureLabels } from '../test/allure'
import AuthCallbackView from '../views/AuthCallbackView.vue'

describe('AuthCallbackView', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('Auth Callback')
    vi.resetModules()
  })

  it('immediately redirects to / on mount', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback')

    mount(AuthCallbackView, {
      global: { plugins: [createPinia(), router] },
    })
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/')
  })

  it('renders a signing-in message while the redirect resolves', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/auth/callback', component: AuthCallbackView },
        { path: '/', component: { template: '<div>home</div>' } },
      ],
    })
    await router.push('/auth/callback')

    const wrapper = mount(AuthCallbackView, {
      global: { plugins: [createPinia(), router] },
    })

    expect(wrapper.text()).toContain('Signing you in')
  })
})
