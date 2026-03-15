import { test, expect } from '@playwright/test'
import { allure } from 'allure-playwright'
import { SequenceListPage } from './pages/SequenceListPage'
import { FormDialog, DeleteDialog } from './pages/dialogs'
import { createSequence, deleteSequence, injectAuthToken } from './helpers/api'

test.describe('Sequence CRUD dialogs', () => {
  test.beforeEach(async ({ page }) => {
    await allure.epic('E2E')
    await allure.feature('Sequences')
    await allure.story('CRUD')
    await injectAuthToken(page)
  })
  test('create: opens form, fills name, submits → row visible', async ({ page }) => {
    const name = `create-test-${Date.now()}`
    const listPage = new SequenceListPage(page)
    const dialog = new FormDialog(page)
    await listPage.goto()

    // Intercept the POST response to capture the id before it's lost
    const responsePromise = page.waitForResponse((r) => r.url().includes('/sequences') && r.request().method() === 'POST')

    await listPage.newButton.click()
    await expect(dialog.dialog).toBeVisible()
    await test.info().attach('create dialog open', { body: await page.screenshot(), contentType: 'image/png' })
    await dialog.fill(name, 'created via e2e')
    await dialog.submit()

    const response = await responsePromise
    const { id: createdId } = await response.json() as { id: number }

    await expect(dialog.dialog).not.toBeVisible()
    await expect(listPage.row(name)).toBeVisible()
    await test.info().attach('row visible after create', { body: await page.screenshot(), contentType: 'image/png' })

    await deleteSequence(createdId)
  })

  test('create cancel: row count unchanged after cancel', async ({ page }) => {
    const listPage = new SequenceListPage(page)
    const dialog = new FormDialog(page)

    await listPage.goto()
    const before = await listPage.rowCount()
    await listPage.newButton.click()
    await expect(dialog.dialog).toBeVisible()
    await test.info().attach('create dialog open', { body: await page.screenshot(), contentType: 'image/png' })
    await dialog.cancelButton.click()
    await expect(dialog.dialog).not.toBeVisible()
    expect(await listPage.rowCount()).toBe(before)
    await test.info().attach('list unchanged after cancel', { body: await page.screenshot(), contentType: 'image/png' })
  })

  test('edit: opens edit dialog, updates name → row reflects new name', async ({ page }) => {
    const original = `edit-orig-${Date.now()}`
    const updated = `edit-upd-${Date.now()}`
    const id = await createSequence(original)

    try {
      const listPage = new SequenceListPage(page)
      const dialog = new FormDialog(page)

      await listPage.goto()
      await listPage.editButtonFor(original).click()
      await expect(dialog.dialog).toBeVisible()
      await test.info().attach('edit dialog open', { body: await page.screenshot(), contentType: 'image/png' })
      await dialog.nameInput.clear()
      await dialog.fill(updated)
      await dialog.submit()
      await expect(dialog.dialog).not.toBeVisible()
      await expect(listPage.row(updated)).toBeVisible()
      await test.info().attach('row updated', { body: await page.screenshot(), contentType: 'image/png' })
    } finally {
      await deleteSequence(id)
    }
  })

  test('delete: opens delete dialog, confirms → row no longer visible', async ({ page }) => {
    const name = `delete-test-${Date.now()}`
    await createSequence(name)

    const listPage = new SequenceListPage(page)
    const dialog = new DeleteDialog(page)

    await listPage.goto()
    await listPage.deleteButtonFor(name).click()
    await expect(dialog.dialog).toBeVisible()
    await test.info().attach('delete dialog open', { body: await page.screenshot(), contentType: 'image/png' })
    await dialog.confirm()
    await expect(dialog.dialog).not.toBeVisible()
    await expect(listPage.row(name)).not.toBeVisible()
    await test.info().attach('row removed after delete', { body: await page.screenshot(), contentType: 'image/png' })
  })
})
