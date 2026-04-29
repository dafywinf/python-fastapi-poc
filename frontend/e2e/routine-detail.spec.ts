import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { RoutineDetailPage } from './pages/RoutineDetailPage'

const mockRoutine = {
  id: 1,
  name: 'Morning Lights',
  description: 'Wake-up scene',
  schedule_type: 'cron',
  schedule_config: { cron: '0 7 * * *' },
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  actions: [
    {
      id: 101,
      position: 1,
      action_type: 'echo',
      config: { message: 'Good morning!' },
    },
  ],
}

test.describe('Routine Detail (mocked)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Routine Detail UI (mocked)')
  })

  test('renders routine name and action buttons', async ({ page }) => {
    await allure.story('Render')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/1', mockRoutine)

    const detailPage = new RoutineDetailPage(page)
    await detailPage.goto(1)

    await expect(detailPage.header).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Morning Lights' })).toBeVisible()
    await expect(detailPage.runButton).toBeVisible()
    await expect(detailPage.editButton).toBeVisible()

    await test.info().attach('routine detail', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('shows action list', async ({ page }) => {
    await allure.story('Actions')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/1', mockRoutine)

    const detailPage = new RoutineDetailPage(page)
    await detailPage.goto(1)

    await expect(page.getByText('echo').first()).toBeVisible()
  })

  test('shows error when routine is not found', async ({ page }) => {
    await allure.story('Error state')
    await mockAuthMe(page)
    await mockApi(page).error('/routines/999', 404, 'Not found')

    const detailPage = new RoutineDetailPage(page)
    await detailPage.goto(999)

    await expect(detailPage.errorBanner).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Routine not found')).toBeVisible()
  })
})
