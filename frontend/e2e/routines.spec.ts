import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { createAction, createRoutine, deleteRoutinesByName, injectAuthToken } from './helpers/api'
import { RoutinesPage } from './pages/RoutinesPage'

test.describe('Routines', () => {
  let token: string

  test.beforeEach(async ({ page }) => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Routines UI')
    token = await injectAuthToken(page)
    await deleteRoutinesByName('E2E Test Routine', token)
    await deleteRoutinesByName('E2E Run Routine', token)
  })

  test('home page loads with three panels', async ({ page }) => {
    await allure.story('Dashboard')
    const routinesPage = new RoutinesPage(page)
    await routinesPage.goto()
    await expect(routinesPage.heading).toBeVisible()
    await expect(routinesPage.executingPanel).toBeVisible()
    await expect(routinesPage.historyPanel).toBeVisible()
    await test.info().attach('routines home', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('creates a routine and it appears in the table', async ({ page }) => {
    await allure.story('CRUD')
    const routinesPage = new RoutinesPage(page)
    await routinesPage.goto()

    // Click new routine
    await routinesPage.newButton.click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()

    // Fill form
    await dialog.getByPlaceholder('Enter name').fill('E2E Test Routine')
    await dialog.getByRole('button', { name: 'Create' }).click()

    // Row should appear
    await expect(routinesPage.row('E2E Test Routine')).toBeVisible()
    await test.info().attach('routine created', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('run now starts a routine and records it in recent history', async ({
    page,
  }) => {
    await allure.story('Execution')
    const routine = await createRoutine('E2E Run Routine', token)
    await createAction(routine.id, {
      action_type: 'echo',
      config: { message: 'hello from e2e' },
    }, token)

    const routinesPage = new RoutinesPage(page)
    await routinesPage.goto()

    const row = routinesPage.row('E2E Run Routine')
    await expect(row).toBeVisible()
    await row.getByRole('button', { name: '▶ Run' }).click()

    await expect(page.getByText('E2E Run Routine is running')).toBeVisible()
    await expect(routinesPage.historyPanel).toBeVisible()
  })
})
