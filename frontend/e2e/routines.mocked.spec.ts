import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { RoutinesPage } from './pages/RoutinesPage'

const mockRoutines = [
  {
    id: 1,
    name: 'Morning Lights',
    description: 'Wake-up scene',
    schedule_type: 'cron',
    schedule_config: { cron: '0 7 * * *' },
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    actions: [],
  },
  {
    id: 2,
    name: 'Evening Wind-Down',
    description: null,
    schedule_type: 'manual',
    schedule_config: null,
    is_active: false,
    created_at: '2026-01-02T00:00:00Z',
    actions: [],
  },
]

const routinesPage = { items: mockRoutines, total: 2, limit: 25, offset: 0 }
const emptyPage = { items: [], total: 0, limit: 25, offset: 0 }

test.describe('Routines (mocked)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Routines UI (mocked)')
  })

  test('renders a list of routines from mocked GET /routines/', async ({ page }) => {
    await allure.story('List')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/', routinesPage)

    const routines = new RoutinesPage(page)
    await routines.goto()

    await expect(routines.heading).toBeVisible()
    await expect(routines.row('Morning Lights')).toBeVisible()
    await expect(routines.row('Evening Wind-Down')).toBeVisible()

    await test.info().attach('routines list', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('shows empty table when API returns no routines', async ({ page }) => {
    await allure.story('Empty state')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/', emptyPage)

    const routines = new RoutinesPage(page)
    await routines.goto()

    await expect(routines.heading).toBeVisible()
    // Table renders with headers but no data rows
    await expect(page.getByRole('columnheader', { name: 'Name' })).toBeVisible()
    await expect(routines.row('Morning Lights')).not.toBeVisible()
  })

  test('shows error banner when API returns 500', async ({ page }) => {
    await allure.story('Error state')
    await mockAuthMe(page)
    await mockApi(page).error('/routines/', 500, 'Failed to load routines')

    const routines = new RoutinesPage(page)
    await routines.goto()

    await expect(page.getByTestId('routines-error')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Failed to load routines')).toBeVisible()
  })

  test('shows action buttons for authenticated user', async ({ page }) => {
    await allure.story('Auth')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/', routinesPage)

    const routines = new RoutinesPage(page)
    await routines.goto()

    await expect(page.getByTestId('run-btn-1')).toBeVisible()
    await expect(page.getByTestId('edit-btn-1')).toBeVisible()
    await expect(page.getByTestId('delete-btn-1')).toBeVisible()
  })
})
