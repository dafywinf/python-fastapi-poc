import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import LoginView from '../views/LoginView.vue'

describe('LoginView', () => {
  it('renders a sign-in button', () => {
    const wrapper = mount(LoginView, {
      global: { stubs: { RouterLink: true } },
    })
    expect(wrapper.text()).toContain('Sign in with Google')
  })

  it('sign-in button links to /auth/google/login', () => {
    const wrapper = mount(LoginView, {
      global: { stubs: { RouterLink: true } },
    })
    const link = wrapper.find('a[href="/auth/google/login"]')
    expect(link.exists()).toBe(true)
  })
})
