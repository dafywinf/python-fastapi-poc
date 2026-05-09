import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { ExecutionHistoryPage } from './pages/ExecutionHistoryPage'

const emptyRoutinesPage = { items: [], total: 0, limit: 25, offset: 0 }
const emptyHistoryPage = { items: [], total: 0, limit: 25, offset: 0 }

const mockCompletedExecution = {
  id: 1,
  routine_id: 10,
  routine_name: 'Morning Routine',
  status: 'completed',
  triggered_by: 'manual',
  queued_at: '2026-01-01T08:00:00Z',
  scheduled_for: '2026-01-01T08:00:00Z',
  started_at: '2026-01-01T08:00:01Z',
  completed_at: '2026-01-01T08:00:10Z',
  action_executions: [],
}

test.describe('Execution History (mocked)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Execution History UI (mocked)')
  })

  test('renders page heading and list container', async ({ page }) => {
    await allure.story('Render')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/', emptyRoutinesPage)
    await mockApi(page).get('/executions/history', emptyHistoryPage)

    const historyPage = new ExecutionHistoryPage(page)
    await historyPage.goto()

    await expect(historyPage.heading).toBeVisible()
    await expect(historyPage.list).toBeVisible()

    await test.info().attach('execution history', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('shows empty state when no executions', async ({ page }) => {
    await allure.story('Empty state')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/', emptyRoutinesPage)
    await mockApi(page).get('/executions/history', emptyHistoryPage)

    const historyPage = new ExecutionHistoryPage(page)
    await historyPage.goto()

    await expect(historyPage.emptyMessage).toBeVisible()
    await expect(page.getByText('No executions found')).toBeVisible()
  })

  test('renders a completed execution card', async ({ page }) => {
    await allure.story('Execution card')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/', emptyRoutinesPage)
    await mockApi(page).get('/executions/history', { items: [mockCompletedExecution], total: 1, limit: 25, offset: 0 })

    const historyPage = new ExecutionHistoryPage(page)
    await historyPage.goto()

    await expect(page.getByText('Morning Routine')).toBeVisible()
    await expect(page.getByText('completed', { exact: true })).toBeVisible()
  })

  test('shows error banner when history API returns 500', async ({ page }) => {
    await allure.story('Error state')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/', emptyRoutinesPage)
    await mockApi(page).error('/executions/history', 500, 'Failed to load history')

    const historyPage = new ExecutionHistoryPage(page)
    await historyPage.goto()

    await expect(historyPage.errorBanner).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Failed to load history')).toBeVisible()
  })
})
