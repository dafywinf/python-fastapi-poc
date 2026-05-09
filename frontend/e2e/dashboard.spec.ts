import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { DashboardPage } from './pages/DashboardPage'

const emptyRoutinesPage = { items: [], total: 0, limit: 25, offset: 0 }
const emptyHistoryPage = { items: [], total: 0, limit: 100, offset: 0 }

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

const mockHistoryItem = {
  id: 5,
  routine_id: 10,
  routine_name: 'Backup Routine',
  status: 'completed',
  triggered_by: 'cron',
  queued_at: '2026-01-01T07:00:00Z',
  scheduled_for: '2026-01-01T07:00:00Z',
  started_at: '2026-01-01T07:00:01Z',
  completed_at: '2026-01-01T07:00:10Z',
  action_executions: [],
}

test.describe('Dashboard (mocked)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Dashboard UI (mocked)')
  })

  test('renders page heading and all three panels', async ({ page }) => {
    await allure.story('Render')
    await mockAuthMe(page)
    await mockApi(page).get('/executions/active', [])
    await mockApi(page).get('/executions/history', emptyHistoryPage)
    await mockApi(page).get('/routines/', emptyRoutinesPage)

    const dashboard = new DashboardPage(page)
    await dashboard.goto()

    await expect(dashboard.heading).toBeVisible()
    await expect(dashboard.queuePanel).toBeVisible()
    await expect(dashboard.historyPanel).toBeVisible()
    await expect(dashboard.routinesPanel).toBeVisible()

    await test.info().attach('dashboard', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('shows empty queue when no active executions', async ({ page }) => {
    await allure.story('Empty queue')
    await mockAuthMe(page)
    await mockApi(page).get('/executions/active', [])
    await mockApi(page).get('/executions/history', emptyHistoryPage)
    await mockApi(page).get('/routines/', emptyRoutinesPage)

    const dashboard = new DashboardPage(page)
    await dashboard.goto()

    await expect(dashboard.emptyQueue).toBeVisible()
    await expect(page.getByText('Queue is empty')).toBeVisible()
  })

  test('shows a running execution in the queue panel', async ({ page }) => {
    await allure.story('Running execution')
    await mockAuthMe(page)
    await mockApi(page).get('/executions/active', [mockRunning])
    await mockApi(page).get('/executions/history', emptyHistoryPage)
    await mockApi(page).get('/routines/', emptyRoutinesPage)

    const dashboard = new DashboardPage(page)
    await dashboard.goto()

    await expect(page.getByText('Morning Routine')).toBeVisible()
    await expect(page.getByText('running', { exact: true })).toBeVisible()
  })

  test('shows a completed execution in the history panel', async ({ page }) => {
    await allure.story('History item')
    await mockAuthMe(page)
    await mockApi(page).get('/executions/active', [])
    await mockApi(page).get('/executions/history', { items: [mockHistoryItem], total: 1, limit: 100, offset: 0 })
    await mockApi(page).get('/routines/', emptyRoutinesPage)

    const dashboard = new DashboardPage(page)
    await dashboard.goto()

    await expect(page.getByText('Backup Routine')).toBeVisible()
    await expect(page.getByText('completed', { exact: true })).toBeVisible()
  })
})
