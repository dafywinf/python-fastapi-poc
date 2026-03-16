import { test, expect, request as pwRequest } from '@playwright/test'
import { SequenceListPage } from './pages/SequenceListPage'
import { SequenceDetailPage } from './pages/SequenceDetailPage'
import { FormDialog, DeleteDialog } from './pages/dialogs'

const BASE_API = 'http://localhost:8000'

async function createSequence(name: string): Promise<number> {
  const ctx = await pwRequest.newContext({ baseURL: BASE_API })
  const res = await ctx.post('/sequences', { data: { name, description: null } })
  const body = await res.json() as { id: number }
  await ctx.dispose()
  return body.id
}

async function deleteSequence(id: number): Promise<void> {
  const ctx = await pwRequest.newContext({ baseURL: BASE_API })
  await ctx.delete(`/sequences/${id}`)
  await ctx.dispose()
}

test.describe('Sequence Detail View', () => {
  test('navigating to detail URL shows correct heading', async ({ page }) => {
    const name = `detail-nav-${Date.now()}`
    const id = await createSequence(name)

    try {
      const detailPage = new SequenceDetailPage(page)
      await detailPage.goto(id)
      await expect(detailPage.heading(name)).toBeVisible()
      await test.info().attach('detail page', { body: await page.screenshot(), contentType: 'image/png' })
    } finally {
      await deleteSequence(id)
    }
  })

  test('back link returns to sequences list', async ({ page }) => {
    const name = `detail-back-${Date.now()}`
    const id = await createSequence(name)

    try {
      const detailPage = new SequenceDetailPage(page)
      await detailPage.goto(id)
      await test.info().attach('detail page before back', { body: await page.screenshot(), contentType: 'image/png' })
      await detailPage.backLink.click()
      await expect(page).toHaveURL(/\/sequences$/)
      await expect(new SequenceListPage(page).heading).toBeVisible()
      await test.info().attach('list page after back', { body: await page.screenshot(), contentType: 'image/png' })
    } finally {
      await deleteSequence(id)
    }
  })

  test('edit from detail view updates heading', async ({ page }) => {
    const original = `detail-edit-orig-${Date.now()}`
    const updated = `detail-edit-upd-${Date.now()}`
    const id = await createSequence(original)

    try {
      const detailPage = new SequenceDetailPage(page)
      const dialog = new FormDialog(page)

      await detailPage.goto(id)
      await detailPage.editButton.click()
      await expect(dialog.dialog).toBeVisible()
      await test.info().attach('edit dialog open', { body: await page.screenshot(), contentType: 'image/png' })
      await dialog.nameInput.clear()
      await dialog.fill(updated)
      await dialog.submit()
      await expect(dialog.dialog).not.toBeVisible()
      await expect(detailPage.heading(updated)).toBeVisible()
      await test.info().attach('heading updated', { body: await page.screenshot(), contentType: 'image/png' })
    } finally {
      await deleteSequence(id)
    }
  })

  test('delete from detail redirects to /sequences', async ({ page }) => {
    const name = `detail-delete-${Date.now()}`
    const id = await createSequence(name)

    const detailPage = new SequenceDetailPage(page)
    const dialog = new DeleteDialog(page)

    try {
      await detailPage.goto(id)
      await detailPage.deleteButton.click()
      await expect(dialog.dialog).toBeVisible()
      await test.info().attach('delete dialog open', { body: await page.screenshot(), contentType: 'image/png' })
      await dialog.confirm()
      await expect(page).toHaveURL(/\/sequences$/)
      await test.info().attach('redirected to list', { body: await page.screenshot(), contentType: 'image/png' })
    } finally {
      // Record may already be deleted by the test — ignore 404
      await deleteSequence(id).catch(() => undefined)
    }
  })
})
