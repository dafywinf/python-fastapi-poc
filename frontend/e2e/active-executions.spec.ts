import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { ActiveExecutionsPage } from './pages/ActiveExecutionsPage'

const mockRunning = {
  id: 1,
  routine_id: 10,
  routine_name: 'Morning Routine',
  status: 'running',
  triggered_by: 'manual',
  queued_at: '2026-01-01T08:00:00Z',
  scheduled_for: '2026-01-01T08:00:00Z',
  started_at: '2026-01-01T08:00:01Z',
  completed_at: null,
  action_executions: [],
}

test.describe('Active Executions (mocked)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Active Executions UI (mocked)')
  })

  test('renders the page heading', async ({ page }) => {
    await allure.story('Render')
    await mockAuthMe(page)
    await mockApi(page).get('/executions/active', [])

    const execPage = new ActiveExecutionsPage(page)
    await execPage.goto()

    await expect(execPage.heading).toBeVisible()

    await test.info().attach('active executions page', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('shows empty queue when no active executions', async ({ page }) => {
    await allure.story('Empty state')
    await mockAuthMe(page)
    await mockApi(page).get('/executions/active', [])

    const execPage = new ActiveExecutionsPage(page)
    await execPage.goto()

    await expect(execPage.emptyMessage).toBeVisible()
    await expect(page.getByText('Queue is empty')).toBeVisible()
  })

  test('shows a running execution card', async ({ page }) => {
    await allure.story('Running execution')
    await mockAuthMe(page)
    await mockApi(page).get('/executions/active', [mockRunning])

    const execPage = new ActiveExecutionsPage(page)
    await execPage.goto()

    await expect(execPage.executionCard('Morning Routine')).toBeVisible()
    await expect(page.getByText('running', { exact: true })).toBeVisible()
  })

  test('shows error banner when API returns 500', async ({ page }) => {
    await allure.story('Error state')
    await mockAuthMe(page)
    await mockApi(page).error('/executions/active', 500, 'Failed to load queue')

    const execPage = new ActiveExecutionsPage(page)
    await execPage.goto()

    await expect(execPage.errorBanner).toBeVisible({ timeout: 15_000 })
  })
})
