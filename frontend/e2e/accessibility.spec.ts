import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import AxeBuilder from '@axe-core/playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'

test.describe('Accessibility', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Accessibility')
  })

  test('login page has no obvious accessibility violations', async ({
    page,
  }) => {
    await allure.story('Login page')
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()

    const accessibilityScanResults = await new AxeBuilder({ page })
      .include('body')
      .analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })
})
