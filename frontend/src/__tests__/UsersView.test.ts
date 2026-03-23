import { flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as allure from 'allure-js-commons'
import type { paths } from '../api/generated/schema'
import { applyFrontendAllureLabels } from '../test/allure'
import { usersHandlers } from '../test/msw/handlers'
import { server } from '../test/msw/server'
import { mountWithApp } from '../test/utils/render'
import UsersView from '../views/UsersView.vue'

type ListUsersResponse =
  paths['/users/']['get']['responses']['200']['content']['application/json']

const mockUsers: ListUsersResponse = [
  {
    id: 1,
    email: 'alice@example.com',
    name: 'Alice',
    picture: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    email: 'bob@example.com',
    name: 'Bob',
    picture: 'https://img.example.com/bob.jpg',
    created_at: '2026-01-02T00:00:00Z',
  },
]

describe('UsersView', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('Users View')
    vi.resetAllMocks()
  })

  it('renders a list of users after loading', async () => {
    server.use(usersHandlers.list(mockUsers))
    const wrapper = await mountWithApp(UsersView)
    await flushPromises()

    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('alice@example.com')
    expect(wrapper.text()).toContain('Bob')
  })

  it('shows a loading state initially', async () => {
    server.use(usersHandlers.pending())
    const wrapper = await mountWithApp(UsersView)
    expect(wrapper.text()).toContain('Loading')
  })

  it('shows an error message when the fetch fails', async () => {
    server.use(usersHandlers.error(500, 'Network error'))
    const wrapper = await mountWithApp(UsersView)
    await flushPromises()
    expect(wrapper.text()).toContain('Network error')
  })
})
