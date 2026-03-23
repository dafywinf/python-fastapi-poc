import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { injectAuthToken } from './helpers/api'

/**
 * Auth flow E2E tests.
 *
 * These tests do NOT contact Google. injectAuthToken() obtains a JWT via
 * POST /auth/token (registered when ENABLE_PASSWORD_AUTH=true) and injects
 * it directly into localStorage — simulating a completed OAuth login.
 */

const FRONTEND_URL = 'http://127.0.0.1:5173'

test.describe('Auth UI', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Auth UI')
  })

  test('unauthenticated user sees Sign in button in navbar', async ({
    page,
  }) => {
    await allure.story('Unauthenticated state')
    await page.goto(`${FRONTEND_URL}/routines`)
    await expect(page.getByText('Sign in with Google')).toBeVisible()
  })

  test('authenticated user sees their email in navbar', async ({ page }) => {
    await allure.story('Authenticated state')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/routines`)
    await expect(page.getByTestId('user-email')).toContainText('admin')
    await expect(page.getByText('Logout')).toBeVisible()
  })

  test('authenticated user sees New Routine button on routines page', async ({
    page,
  }) => {
    await allure.story('Authenticated state')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/routines`)
    await expect(
      page.getByRole('button', { name: /new routine/i }),
    ).toBeVisible()
  })

  test('unauthenticated user does not see New Routine button', async ({
    page,
  }) => {
    await allure.story('Unauthenticated state')
    await page.goto(`${FRONTEND_URL}/routines`)
    await expect(
      page.getByRole('button', { name: /new routine/i }),
    ).not.toBeVisible()
  })

  test('logout button clears auth state', async ({ page }) => {
    await allure.story('Logout')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/routines`)
    await page.getByText('Logout').click()
    await expect(page.getByText('Sign in with Google')).toBeVisible()
  })
})

test.describe('Users page', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Users Page')
  })

  test('users page redirects to login when unauthenticated', async ({
    page,
  }) => {
    await allure.story('Protected route')
    await page.goto(`${FRONTEND_URL}/users`)
    await expect(page).toHaveURL(/\/login\?redirect=/)
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  })

  test('authenticated user can access users page', async ({ page }) => {
    await allure.story('Protected route')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/users`)
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
  })
})
