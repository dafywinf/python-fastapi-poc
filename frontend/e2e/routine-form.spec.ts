import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { applyFrontendE2EAllureLabels } from './helpers/allure'
import { mockApi, mockAuthMe } from './helpers/mockApi'
import { RoutineFormPage } from './pages/RoutineFormPage'

const mockRoutine = {
  id: 1,
  name: 'Morning Lights',
  description: null,
  schedule_type: 'manual',
  schedule_config: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  actions: [],
}

const createdRoutine = {
  ...mockRoutine,
  id: 42,
  name: 'New Test Routine',
}

test.describe('Routine Form (mocked)', () => {
  test.beforeEach(async () => {
    await applyFrontendE2EAllureLabels('Browser E2E', 'top')
    await allure.feature('Routine Form UI (mocked)')
  })

  test('renders create form with name input and Create button', async ({ page }) => {
    await allure.story('Create mode')
    await mockAuthMe(page)

    const formPage = new RoutineFormPage(page)
    await formPage.gotoCreate()

    await expect(page.getByRole('heading', { name: 'New Routine' })).toBeVisible()
    await expect(formPage.nameInput).toBeVisible()
    await expect(formPage.createButton).toBeVisible()
    await expect(formPage.cancelButton).toBeVisible()

    await test.info().attach('create form', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('fills and submits create form, mocking POST /routines/', async ({ page }) => {
    await allure.story('Create submission')
    await mockAuthMe(page)
    await mockApi(page).post('/routines/', createdRoutine)
    // After create, the app navigates back to the routines list
    await mockApi(page).get('/routines/', { items: [createdRoutine], total: 1, limit: 25, offset: 0 })

    const formPage = new RoutineFormPage(page)
    await formPage.gotoCreate()

    await formPage.nameInput.fill('New Test Routine')
    await formPage.createButton.click()

    // Should land on the routines list page
    await expect(page.getByRole('heading', { name: 'Routines' })).toBeVisible({ timeout: 10_000 })
  })

  test('renders edit form with existing routine name pre-filled', async ({ page }) => {
    await allure.story('Edit mode')
    await mockAuthMe(page)
    await mockApi(page).get('/routines/1', mockRoutine)

    const formPage = new RoutineFormPage(page)
    await formPage.gotoEdit(1)

    await expect(page.getByRole('heading', { name: 'Morning Lights' })).toBeVisible()
    await expect(formPage.nameInput).toHaveValue('Morning Lights')
    await expect(formPage.saveButton).toBeVisible()

    await test.info().attach('edit form', {
      body: await page.screenshot(),
      contentType: 'image/png',
    })
  })

  test('shows error when routine not found in edit mode', async ({ page }) => {
    await allure.story('Edit not found')
    await mockAuthMe(page)
    await mockApi(page).error('/routines/999', 404, 'Not found')

    const formPage = new RoutineFormPage(page)
    await formPage.gotoEdit(999)

    await expect(formPage.pageError).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText('Routine not found')).toBeVisible()
  })
})
