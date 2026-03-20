import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import UsersView from '../views/UsersView.vue'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

const mockUsers = [
  { id: 1, email: 'alice@example.com', name: 'Alice', picture: null, created_at: '2026-01-01T00:00:00Z' },
  { id: 2, email: 'bob@example.com', name: 'Bob', picture: 'https://img.example.com/bob.jpg', created_at: '2026-01-02T00:00:00Z' },
]

describe('UsersView', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders a list of users after loading', async () => {
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => mockUsers,
    } as Response)

    const wrapper = mount(UsersView)
    await flushPromises()

    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('alice@example.com')
    expect(wrapper.text()).toContain('Bob')
  })

  it('shows a loading state initially', () => {
    vi.spyOn(global, 'fetch').mockImplementation(() => new Promise(() => {}))
    const wrapper = mount(UsersView)
    expect(wrapper.text()).toContain('Loading')
  })

  it('shows an error message when the fetch fails', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Network error'))
    const wrapper = mount(UsersView)
    await flushPromises()
    expect(wrapper.text()).toMatch(/error|failed/i)
  })
})
