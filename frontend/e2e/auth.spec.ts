import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { injectAuthToken } from './helpers/api'

/**
 * Auth flow E2E tests.
 *
 * These tests do NOT contact Google. injectAuthToken() obtains a JWT via
 * POST /auth/token (registered when ENABLE_PASSWORD_AUTH=true) and injects
 * it directly into localStorage — simulating a completed OAuth login.
 */

const FRONTEND_URL = 'http://localhost:5173'

test.describe('Auth UI', () => {
  test.beforeEach(async () => {
    await allure.epic('Frontend')
    await allure.feature('Auth UI')
  })

  test('unauthenticated user sees Sign in button in navbar', async ({ page }) => {
    await allure.story('Unauthenticated state')
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.getByText('Sign in with Google')).toBeVisible()
  })

  test('authenticated user sees their email in navbar', async ({ page }) => {
    await allure.story('Authenticated state')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.locator('.navbar__user-email')).toContainText('admin')
    await expect(page.getByText('Logout')).toBeVisible()
  })

  test('authenticated user sees Create button on sequences page', async ({ page }) => {
    await allure.story('Authenticated state')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/sequences`)
    // The Create button is labelled "New Sequence" in the UI
    await expect(page.getByRole('button', { name: /new sequence/i })).toBeVisible()
  })

  test('unauthenticated user does not see Create button', async ({ page }) => {
    await allure.story('Unauthenticated state')
    await page.goto(`${FRONTEND_URL}/sequences`)
    // The Create button is labelled "New Sequence" in the UI
    await expect(page.getByRole('button', { name: /new sequence/i })).not.toBeVisible()
  })

  test('logout button clears auth state', async ({ page }) => {
    await allure.story('Logout')
    await injectAuthToken(page)
    await page.goto(`${FRONTEND_URL}/sequences`)
    await page.getByText('Logout').click()
    await expect(page.getByText('Sign in with Google')).toBeVisible()
  })
})

test.describe('Users page', () => {
  test.beforeEach(async () => {
    await allure.epic('Frontend')
    await allure.feature('Users Page')
  })

  test('users page is accessible without login', async ({ page }) => {
    await allure.story('Public access')
    await page.goto(`${FRONTEND_URL}/users`)
    await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
  })

  test('users page shows the Users nav link', async ({ page }) => {
    await allure.story('Navigation')
    await page.goto(`${FRONTEND_URL}/sequences`)
    await expect(page.getByRole('link', { name: 'Users' })).toBeVisible()
  })
})
