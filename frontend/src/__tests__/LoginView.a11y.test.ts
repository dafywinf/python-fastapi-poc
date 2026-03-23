import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import * as allure from 'allure-js-commons'
import { axe } from 'vitest-axe'
import { applyFrontendAllureLabels } from '../test/allure'
import LoginView from '../views/LoginView.vue'

describe('LoginView accessibility', () => {
  beforeEach(() => {
    applyFrontendAllureLabels('Vitest', 'base')
    allure.feature('Login View')
  })

  it('has no obvious accessibility violations', async () => {
    const wrapper = mount(LoginView)
    const results = await axe(wrapper.element)
    expect(results.violations).toEqual([])
  })
})
