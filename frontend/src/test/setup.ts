import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { server } from './msw/server'

beforeAll(() => {
  if (!window.matchMedia) {
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: (query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: () => {},
        removeListener: () => {},
        addEventListener: () => {},
        removeEventListener: () => {},
        dispatchEvent: () => false,
      }),
    })
  }
  server.listen({ onUnhandledRequest: 'error' })
})

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  if (typeof localStorage.clear === 'function') {
    localStorage.clear()
  }
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})
