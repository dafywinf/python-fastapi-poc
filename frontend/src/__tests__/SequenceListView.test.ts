/**
 * Component tests for SequenceListView.
 *
 * The sequencesApi module is mocked with vi.mock — components should not know
 * or care about HTTP; they call the API and react to the results.  Native
 * <dialog> methods are polyfilled because jsdom does not implement them.
 */

import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import * as allure from 'allure-js-commons'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import SequenceListView from '../views/SequenceListView.vue'
import { sequencesApi } from '../api/sequences'
import type { Sequence } from '../types/sequence'

// ── Module mock ──────────────────────────────────────────────────────────────
// vi.mock is hoisted before imports — sequencesApi is fully replaced.
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

const SEQUENCES: Sequence[] = [
  { id: 1, name: 'Alpha', description: 'First sequence', created_at: '2026-01-01T00:00:00Z' },
  { id: 2, name: 'Beta', description: null, created_at: '2026-01-02T00:00:00Z' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/sequences', component: SequenceListView },
      { path: '/sequences/:id', component: { template: '<div />' } },
    ],
  })
}

function mountView() {
  return mount(SequenceListView, {
    global: { plugins: [makeRouter()] },
  })
}

// ── Global teardown ───────────────────────────────────────────────────────────
// vi.resetAllMocks resets implementations (not just call counts), preventing
// mock state from a previous suite bleeding into the next test.
afterEach(() => vi.resetAllMocks())

// ── Suites ────────────────────────────────────────────────────────────────────

describe('SequenceListView — initial render', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('List')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.list).mockResolvedValue(SEQUENCES)
  })

  it('shows a loading indicator while the API call is in-flight', async () => {
    vi.mocked(sequencesApi.list).mockReturnValue(new Promise(() => {}))

    const wrapper = mountView()
    // onMounted fires synchronously; loading.value = true is set, but Vue
    // batches DOM updates — await nextTick so the DOM reflects the new state.
    await nextTick()

    expect(wrapper.text()).toContain('Loading…')
  })

  it('renders a data row for each sequence returned by the API', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.findAll('tr.data-row')).toHaveLength(2)
  })

  it('renders sequence names in the table', async () => {
    const wrapper = mountView()
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('Alpha')
    expect(text).toContain('Beta')
  })

  it('renders — for a null description', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('—')
  })

  it('shows the empty-state message when the API returns an empty array', async () => {
    vi.mocked(sequencesApi.list).mockResolvedValue([])
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('No sequences found')
    expect(wrapper.findAll('tr.data-row')).toHaveLength(0)
  })

  it('shows an error banner when the API rejects', async () => {
    vi.mocked(sequencesApi.list).mockRejectedValue(new Error('Network error'))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.alert--error').text()).toBe('Network error')
  })
})

describe('SequenceListView — sorting', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('List')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.list).mockResolvedValue([
      { id: 2, name: 'Beta', description: null, created_at: '2026-01-02T00:00:00Z' },
      { id: 1, name: 'Alpha', description: null, created_at: '2026-01-01T00:00:00Z' },
    ])
  })

  it('sorts rows by name ascending when the Name column header is clicked', async () => {
    const wrapper = mountView()
    await flushPromises()

    const nameHeader = wrapper.findAll('th').find((th) => th.text().includes('Name'))!
    await nameHeader.trigger('click')

    const rows = wrapper.findAll('tr.data-row')
    expect(rows[0].text()).toContain('Alpha')
    expect(rows[1].text()).toContain('Beta')
  })

  it('reverses sort order when the Name column header is clicked twice', async () => {
    const wrapper = mountView()
    await flushPromises()

    const nameHeader = wrapper.findAll('th').find((th) => th.text().includes('Name'))!
    await nameHeader.trigger('click')
    await nameHeader.trigger('click')

    const rows = wrapper.findAll('tr.data-row')
    expect(rows[0].text()).toContain('Beta')
    expect(rows[1].text()).toContain('Alpha')
  })
})

describe('SequenceListView — create dialog', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('Create')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.list).mockResolvedValue(SEQUENCES)
  })

  it('calls showModal when + New Sequence is clicked', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button.btn--primary').trigger('click')

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
  })

  it('submits the create form and prepends the new row to the table', async () => {
    const created: Sequence = { id: 3, name: 'Gamma', description: null, created_at: '2026-01-03T00:00:00Z' }
    vi.mocked(sequencesApi.create).mockResolvedValue(created)

    const wrapper = mountView()
    await flushPromises()

    await allure.step('Open create dialog and fill the form', async () => {
      await wrapper.find('button.btn--primary').trigger('click')
      await wrapper.find('#seq-name').setValue('Gamma')
    })

    await allure.step('Submit the form and wait for the API call', async () => {
      await wrapper.find('form').trigger('submit')
      await flushPromises()
    })

    await allure.step('Verify API was called and row was added', async () => {
      expect(sequencesApi.create).toHaveBeenCalledWith({ name: 'Gamma', description: null })
      expect(wrapper.findAll('tr.data-row')).toHaveLength(3)
      expect(wrapper.text()).toContain('Gamma')
    })
  })

  it('shows a form error when the create API rejects', async () => {
    vi.mocked(sequencesApi.create).mockRejectedValue(new Error('Name already taken'))

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button.btn--primary').trigger('click')
    await wrapper.find('#seq-name').setValue('Alpha')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('.alert--error').text()).toBe('Name already taken')
  })
})

describe('SequenceListView — edit dialog', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('Partial Update')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.list).mockResolvedValue(SEQUENCES)
  })

  it('opens the edit dialog pre-populated with the sequence values', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button[title="Edit"]').trigger('click')

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    const nameInput = wrapper.find('#seq-name').element as HTMLInputElement
    expect(nameInput.value).toBe('Alpha')
  })

  it('submits the edit form and updates the row in place', async () => {
    const updated: Sequence = { ...SEQUENCES[0], name: 'Alpha Updated' }
    vi.mocked(sequencesApi.update).mockResolvedValue(updated)

    const wrapper = mountView()
    await flushPromises()

    await allure.step('Open edit dialog for the first row', async () => {
      await wrapper.find('button[title="Edit"]').trigger('click')
    })

    await allure.step('Change the name and submit', async () => {
      await wrapper.find('#seq-name').setValue('Alpha Updated')
      await wrapper.find('form').trigger('submit')
      await flushPromises()
    })

    await allure.step('Verify PATCH was called and row was updated', async () => {
      expect(sequencesApi.update).toHaveBeenCalledWith(1, {
        name: 'Alpha Updated',
        description: 'First sequence',
      })
      expect(wrapper.text()).toContain('Alpha Updated')
    })
  })
})

describe('SequenceListView — delete dialog', () => {
  beforeEach(() => {
    allure.feature('Sequences UI')
    allure.story('Delete')
    HTMLDialogElement.prototype.showModal = vi.fn()
    HTMLDialogElement.prototype.close = vi.fn()
    vi.mocked(sequencesApi.list).mockResolvedValue(SEQUENCES)
  })

  it('opens the delete confirmation dialog when the delete button is clicked', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button[title="Delete"]').trigger('click')

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled()
    expect(wrapper.text()).toContain('Alpha')
  })

  it('removes the row and calls the API after confirming delete', async () => {
    vi.mocked(sequencesApi.delete).mockResolvedValue(undefined)

    const wrapper = mountView()
    await flushPromises()

    await allure.step('Open delete confirmation for the first row', async () => {
      await wrapper.find('button[title="Delete"]').trigger('click')
    })

    await allure.step('Confirm the deletion', async () => {
      await wrapper.find('button.btn--danger').trigger('click')
      // flushPromises resolves the delete() promise; nextTick commits Vue's
      // reactive filter update to the DOM.
      await flushPromises()
      await nextTick()
    })

    await allure.step('Verify DELETE was called and row was removed', async () => {
      expect(sequencesApi.delete).toHaveBeenCalledWith(1)
      const rows = wrapper.findAll('tr.data-row')
      expect(rows).toHaveLength(1)
      expect(rows[0].text()).not.toContain('Alpha')
    })
  })

  it('shows a delete error when the API rejects', async () => {
    vi.mocked(sequencesApi.delete).mockRejectedValue(new Error('Cannot delete'))

    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('button[title="Delete"]').trigger('click')
    await wrapper.find('button.btn--danger').trigger('click')
    await flushPromises()
    await nextTick()

    expect(wrapper.find('.alert--error').text()).toBe('Cannot delete')
    expect(wrapper.findAll('tr.data-row')).toHaveLength(2)
  })
})
