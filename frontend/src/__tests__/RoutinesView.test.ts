import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import { computed, ref } from 'vue'
import type { paths } from '../api/generated/schema'
import { applyFrontendAllureLabels } from '../test/allure'
import { routinesHandlers } from '../test/msw/handlers'
import { server } from '../test/msw/server'
import { mountWithApp } from '../test/utils/render'
import RoutinesView from '../views/RoutinesView.vue'

type ListRoutinesResponse =
  paths['/routines/']['get']['responses']['200']['content']['application/json']

const mockRoutines: ListRoutinesResponse = [
  {
    id: 1,
    name: 'Morning Lights',
    description: 'Wake-up scene',
    schedule_type: 'manual',
    schedule_config: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    actions: [],
  },
]

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

describe('RoutinesView', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('Routines View')
    vi.resetAllMocks()
  })

  it('renders routines after loading', async () => {
    server.use(routinesHandlers.list(mockRoutines))

    const wrapper = await mountWithApp(RoutinesView, {}, '/routines')
    await flushPromises()

    expect(wrapper.text()).toContain('Morning Lights')
    expect(wrapper.text()).toContain('Currently Executing')
    expect(wrapper.text()).toContain('Recent History')
  })

  it('shows a loading state initially', async () => {
    server.use(
      routinesHandlers.listPending(),
      routinesHandlers.activeExecutionsPending(),
      routinesHandlers.executionHistoryPending(),
    )

    const wrapper = await mountWithApp(RoutinesView, {}, '/routines')

    expect(wrapper.text()).toContain('Loading')
  })

  it('shows an error message when the routines fetch fails', async () => {
    server.use(routinesHandlers.listError(500, 'Network error'))

    const wrapper = await mountWithApp(RoutinesView, {}, '/routines')
    await flushPromises()

    expect(wrapper.text()).toContain('Network error')
  })

  it('shows empty state when no routines exist', async () => {
    server.use(routinesHandlers.list([]))

    const wrapper = await mountWithApp(RoutinesView, {}, '/routines')
    await flushPromises()

    expect(wrapper.text()).toContain('Name')
    expect(wrapper.text()).toContain('Schedule')
    expect(wrapper.text()).toContain('None running')
    expect(wrapper.text()).toContain('No history')
  })
})
