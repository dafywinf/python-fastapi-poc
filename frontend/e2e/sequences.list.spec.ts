import { test, expect, request as pwRequest } from '@playwright/test'
import { SequenceListPage } from './pages/SequenceListPage'

const BASE_API = 'http://localhost:8000'

async function createSequence(name: string, description?: string): Promise<number> {
  const ctx = await pwRequest.newContext({ baseURL: BASE_API })
  const res = await ctx.post('/sequences', {
    data: { name, description: description ?? null },
  })
  const body = await res.json() as { id: number }
  await ctx.dispose()
  return body.id
}

async function deleteSequence(id: number): Promise<void> {
  const ctx = await pwRequest.newContext({ baseURL: BASE_API })
  await ctx.delete(`/sequences/${id}`)
  await ctx.dispose()
}

test.describe('Sequence List View', () => {
  test('renders heading and new button', async ({ page }) => {
    const listPage = new SequenceListPage(page)
    await listPage.goto()
    await expect(listPage.heading).toBeVisible()
    await expect(listPage.newButton).toBeVisible()
    await test.info().attach('list page loaded', { body: await page.screenshot(), contentType: 'image/png' })
  })

  test('shows empty state when no sequences exist', async ({ page }) => {
    const listPage = new SequenceListPage(page)
    await listPage.goto()
    // rowCount() already waits for loading to clear before counting
    const count = await listPage.rowCount()
    if (count === 0) {
      await expect(listPage.emptyState).toBeVisible()
      await test.info().attach('empty state', { body: await page.screenshot(), contentType: 'image/png' })
    } else {
      // Environment already has data — skip rather than fail
      test.skip()
    }
  })

  test('renders row after API-created sequence', async ({ page }) => {
    const name = `list-test-${Date.now()}`
    const id = await createSequence(name, 'list test description')

    try {
      const listPage = new SequenceListPage(page)
      await listPage.goto()
      await expect(listPage.row(name)).toBeVisible()
      await test.info().attach('row visible', { body: await page.screenshot(), contentType: 'image/png' })
    } finally {
      await deleteSequence(id)
    }
  })

  test('name link navigates to detail view', async ({ page }) => {
    const name = `link-test-${Date.now()}`
    const id = await createSequence(name)

    try {
      const listPage = new SequenceListPage(page)
      await listPage.goto()
      await listPage.nameLink(name).click()
      await expect(page).toHaveURL(new RegExp(`/sequences/${id}`))
      await test.info().attach('detail view after navigation', { body: await page.screenshot(), contentType: 'image/png' })
    } finally {
      await deleteSequence(id)
    }
  })
})
