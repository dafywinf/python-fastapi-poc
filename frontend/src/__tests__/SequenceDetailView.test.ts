/**
 * Component tests for SequenceDetailView.
 *
 * The sequencesApi module is mocked with vi.mock.  useRouter is tested by
 * providing a real memory-history router and spying on router.push.
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as allure from 'allure-js-commons'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import SequenceDetailView from '../views/SequenceDetailView.vue'
import { sequencesApi } from '../api/sequences'
import type { Sequence } from '../types/sequence'

// ── Module mock ──────────────────────────────────────────────────────────────

vi.mock('../api/sequences', () => ({
  sequencesApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}))

// ── Fixtures ─────────────────────────────────────────────────────────────────

const SEQUENCE: Sequence = {
  id: 42,
  name: 'Alpha',
  description: 'A test sequence',
  created_at: '2026-01-15T10:30:00Z',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/sequences', component: { template: '<div />' } },
      { path: '/sequences/:id', component: SequenceDetailView, props: true },
    ],
  })
}

function mountView(id = 42) {
  return mount(SequenceDetailView, {
    props: { id },
    global: { plugins: [makeRouter()] },
  })
}

// ── Global teardown ───────────────────────────────────────────────────────────
afterEach(() => vi.resetAllMocks())

// ── Suites ────────────────────────────────────────────────────────────────────

describe('SequenceDetailView — initial render', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('Retrieve')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.get).mockResolvedValue(SEQUENCE)
  })

  it('shows a loading indicator while the API call is in-flight', async () => {
    vi.mocked(sequencesApi.get).mockReturnValue(new Promise(() => {}))

    const wrapper = mountView()
    await nextTick()

    expect(wrapper.text()).toContain('Loading…')
  })

  it('renders all sequence fields after loading', async () => {
    const wrapper = mountView()
    await flushPromises()

    await allure.step('Verify all fields are displayed', async () => {
      const text = wrapper.text()
      expect(text).toContain('Alpha')
      expect(text).toContain('A test sequence')
      expect(text).toContain('42')
    })
  })

  it('fetches the sequence using the id prop', async () => {
    mountView(42)
    await flushPromises()

    expect(sequencesApi.get).toHaveBeenCalledWith(42)
  })

  it('shows an error message when the API rejects with a 404', async () => {
    vi.mocked(sequencesApi.get).mockRejectedValue(new Error('Sequence 42 not found'))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.alert--error').text()).toBe('Sequence 42 not found')
  })

  it('renders "No description provided." when description is null', async () => {
    vi.mocked(sequencesApi.get).mockResolvedValue({ ...SEQUENCE, description: null })
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('No description provided.')
  })

  it('renders a back link to /sequences', async () => {
    const wrapper = mountView()
    await flushPromises()

    const link = wrapper.find('a.back-link')
    expect(link.attributes('href')).toBe('/sequences')
  })
})

describe('SequenceDetailView — edit dialog', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('Partial Update')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.get).mockResolvedValue(SEQUENCE)
  })


  it('opens the edit dialog pre-populated when Edit is clicked', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button.btn--ghost').trigger('click')

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    const nameInput = wrapper.find('#edit-name').element as HTMLInputElement
    expect(nameInput.value).toBe('Alpha')
  })

  it('submits the edit form and updates the displayed name', async () => {
    const updated: Sequence = { ...SEQUENCE, name: 'Alpha Updated' }
    vi.mocked(sequencesApi.update).mockResolvedValue(updated)

    const wrapper = mountView()
    await flushPromises()

    await allure.step('Open edit dialog', async () => {
      await wrapper.find('button.btn--ghost').trigger('click')
    })

    await allure.step('Update the name and submit', async () => {
      await wrapper.find('#edit-name').setValue('Alpha Updated')
      await wrapper.find('form').trigger('submit')
      await flushPromises()
    })

    await allure.step('Verify PATCH was called and name is updated in the view', async () => {
      expect(sequencesApi.update).toHaveBeenCalledWith(42, {
        name: 'Alpha Updated',
        description: 'A test sequence',
      })
      expect(wrapper.find('h1').text()).toBe('Alpha Updated')
    })
  })

  it('shows a form error when the update API rejects', async () => {
    vi.mocked(sequencesApi.update).mockRejectedValue(new Error('Update failed'))

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button.btn--ghost').trigger('click')
    await wrapper.find('#edit-name').setValue('New')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.alert--error').text()).toBe('Update failed')
  })
})

describe('SequenceDetailView — delete dialog', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('Delete')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.get).mockResolvedValue(SEQUENCE)
  })


  it('opens the delete confirmation dialog when Delete is clicked', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button.btn--danger-outline').trigger('click')

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Alpha')
  })

  it('navigates to /sequences after a successful delete', async () => {
    vi.mocked(sequencesApi.delete).mockResolvedValue(undefined)

    const router = makeRouter()
    vi.spyOn(router, 'push')

    const wrapper = mount(SequenceDetailView, {
      props: { id: 42 },
      global: { plugins: [router] },
    })
    await flushPromises()

    await allure.step('Open delete dialog and confirm', async () => {
      await wrapper.find('button.btn--danger-outline').trigger('click')
      await wrapper.find('button.btn--danger').trigger('click')
      await flushPromises()
    })

    await allure.step('Verify DELETE was called and router navigated away', async () => {
      expect(sequencesApi.delete).toHaveBeenCalledWith(42)
      expect(router.push).toHaveBeenCalledWith('/sequences')
    })
  })

  it('shows a delete error and stays on the page when the API rejects', async () => {
    vi.mocked(sequencesApi.delete).mockRejectedValue(new Error('Delete failed'))

    const router = makeRouter()
    vi.spyOn(router, 'push')

    const wrapper = mount(SequenceDetailView, {
      props: { id: 42 },
      global: { plugins: [router] },
    })
    await flushPromises()

    await wrapper.find('button.btn--danger-outline').trigger('click')
    await wrapper.find('button.btn--danger').trigger('click')
    await flushPromises()

    expect(wrapper.find('.alert--error').text()).toBe('Delete failed')
    expect(router.push).not.toHaveBeenCalled()
  })
})
