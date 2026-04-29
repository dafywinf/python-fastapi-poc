import { expect, test } from '@playwright/test'
import { allure } from 'allure-playwright'
import type { components } from '../src/api/generated/schema'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { UsersPage } from './pages/UsersPage'

type User = components['schemas']['UserResponse']

const mockUsers: User[] = [
  {
    id: 1,
    email: 'alice@example.com',
    name: 'Alice',
    picture: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    email: 'bob@example.com',
    name: 'Bob',
    picture: 'https://img.example.com/bob.jpg',
    created_at: '2026-01-02T00:00:00Z',
  },
]

test.describe('Users (mocked API)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Users Page')
  })

  test('renders a list of users from mocked GET /users/', async ({ page }) => {
    await allure.story('List')

    // Auth must be mocked before navigation — the router guard fires on goto()
    await mockAuthMe(page)
    await mockApi(page).get('/users/', mockUsers)

    const usersPage = new UsersPage(page)
    await usersPage.goto()

    await expect(usersPage.heading).toBeVisible()
    await expect(usersPage.row('Alice')).toBeVisible()
    await expect(usersPage.row('Bob')).toBeVisible()

    await test.info().attach('users list loaded', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('shows empty state when API returns an empty list', async ({ page }) => {
    await allure.story('Empty state')

    await mockAuthMe(page)
    await mockApi(page).get('/users/', [])

    const usersPage = new UsersPage(page)
    await usersPage.goto()

    await expect(usersPage.emptyMessage).toBeVisible()
    await expect(page.getByText('No users have logged in yet.')).toBeVisible()
  })

  test('shows error banner when API returns 500', async ({ page }) => {
    await allure.story('Error state')

    await mockAuthMe(page)
    await mockApi(page).error('/users/', 500, 'Failed to load users')

    const usersPage = new UsersPage(page)
    await usersPage.goto()

    // The production QueryClient retries failed requests 3 times with exponential
    // backoff (0 + 1s + 2s + 4s ≈ 7s). Allow enough time for all retries to exhaust
    // before the error state becomes visible.
    await expect(usersPage.errorBanner).toBeVisible({ timeout: 15_000 })
    await expect(usersPage.errorBanner).toContainText('Failed to load users')
  })

  test('demonstrates POST /users/ mock interception pattern', async ({ page }) => {
    await allure.story('Create (mock pattern)')

    const newUser: User = {
      id: 3,
      email: 'charlie@example.com',
      name: 'Charlie',
      picture: null,
      created_at: '2026-03-01T00:00:00Z',
    }

    await mockAuthMe(page)
    await mockApi(page).get('/users/', mockUsers)
    await mockApi(page).post('/users/', newUser, 201)

    const usersPage = new UsersPage(page)
    await usersPage.goto()

    await expect(usersPage.row('Alice')).toBeVisible()

    // Verify the POST mock intercepts the request and returns the stubbed response
    const response = await page.evaluate(async () => {
      const res = await fetch('/users/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'charlie@example.com', name: 'Charlie' }),
      })
      return { status: res.status, body: (await res.json()) as unknown }
    })

    expect(response.status).toBe(201)
    expect((response.body as User).name).toBe('Charlie')
  })
})
