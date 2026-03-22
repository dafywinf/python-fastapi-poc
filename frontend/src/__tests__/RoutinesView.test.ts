/**
 * Component tests for RoutinesView.
 *
 * The routinesApi module is mocked with vi.mock — components should not know
 * or care about HTTP; they call the API and react to the results. Native
 * <dialog> methods are polyfilled because jsdom does not implement them.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, type RouteRecordRaw } from 'vue-router'
import { computed, ref } from 'vue'
import * as allure from 'allure-js-commons'
import RoutinesView from '../views/RoutinesView.vue'

vi.mock('../api/routines', () => ({
  routinesApi: {
    list: vi.fn().mockResolvedValue([]),
    activeExecutions: vi.fn().mockResolvedValue([]),
    executionHistory: vi.fn().mockResolvedValue([]),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    runNow: vi.fn(),
  },
}))

vi.mock('../composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: computed(() => true),
    user: computed(() => ({ email: 'test@example.com', name: 'Test' })),
    token: ref('mock-token'),
    setToken: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

// Mock usePolling to avoid interval complexity in component tests
vi.mock('../composables/usePolling', () => ({
  usePolling: vi.fn().mockImplementation((fn: () => Promise<unknown>) => {
    void fn() // call it once for coverage
    return {
      data: ref([]),
      loading: ref(false),
      error: ref(null),
      refresh: vi.fn(),
    }
  }),
}))

HTMLDialogElement.prototype.showModal = vi.fn()
HTMLDialogElement.prototype.close = vi.fn()

function makeRouter(): ReturnType<typeof createRouter> {
  const routes: RouteRecordRaw[] = [
    { path: '/routines', component: RoutinesView },
    { path: '/routines/:id', component: { template: '<div />' } },
  ]
  return createRouter({ history: createMemoryHistory(), routes })
}

describe('RoutinesView', () => {
  beforeEach(() => {
    allure.epic('Frontend')
    allure.feature('RoutinesView')
  })

  it('renders headings', async () => {
    const wrapper = mount(RoutinesView, { global: { plugins: [makeRouter()] } })
    await flushPromises()
    expect(wrapper.text()).toContain('Routines')
    expect(wrapper.text()).toContain('Currently Executing')
    expect(wrapper.text()).toContain('Recent History')
  })

  it('shows empty state when no routines', async () => {
    const wrapper = mount(RoutinesView, { global: { plugins: [makeRouter()] } })
    await flushPromises()
    expect(wrapper.text()).toContain('No routines')
  })
})
