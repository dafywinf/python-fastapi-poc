import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { usePolling } from '../composables/usePolling'
import * as allure from 'allure-js-commons'
import { applyFrontendAllureLabels } from '../test/allure'

// Wrapper component to host the composable in a mounted context
function makeWrapper(fn: () => Promise<unknown>, intervalMs: number) {
  return defineComponent({
    setup() {
      return usePolling(fn, intervalMs)
    },
    render() {
      return h('div')
    },
  })
}

describe('usePolling', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('usePolling')
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('calls fn immediately on mount', async () => {
    const fn = vi.fn().mockResolvedValue([1, 2, 3])
    const wrapper = mount(makeWrapper(fn, 1000))
    await wrapper.vm.$nextTick()
    await Promise.resolve() // flush promise queue
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('loading is true initially then false after first fetch', async () => {
    const fn = vi.fn().mockResolvedValue([])
    const wrapper = mount(makeWrapper(fn, 1000))
    // Loading starts true
    expect(wrapper.vm.loading).toBe(true)
    await wrapper.vm.$nextTick()
    await Promise.resolve()
    expect(wrapper.vm.loading).toBe(false)
  })

  it('polls on interval', async () => {
    const fn = vi.fn().mockResolvedValue([])
    mount(makeWrapper(fn, 1000))
    // Wait for onMounted to run and the initial fetch to resolve, and the
    // interval to be registered
    await flushPromises()
    vi.advanceTimersByTime(3000)
    await flushPromises()
    expect(fn.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('retains last-good data on error', async () => {
    const fn = vi
      .fn()
      .mockResolvedValueOnce([1, 2])
      .mockRejectedValueOnce(new Error('boom'))
    const wrapper = mount(makeWrapper(fn, 1000))
    await flushPromises()
    vi.advanceTimersByTime(1000)
    await flushPromises()
    expect(wrapper.vm.error).toBeInstanceOf(Error)
    expect(wrapper.vm.data).toEqual([1, 2]) // last-good retained
  })

  it('clears interval on unmount', async () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval')
    const fn = vi.fn().mockResolvedValue([])
    const wrapper = mount(makeWrapper(fn, 1000))
    // Wait for onMounted to complete so the interval is registered
    await flushPromises()
    wrapper.unmount()
    expect(clearIntervalSpy).toHaveBeenCalled()
  })
})
