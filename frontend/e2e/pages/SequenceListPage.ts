import { type Page, type Locator } from '@playwright/test'

export class SequenceListPage {
  private readonly page: Page
  readonly heading: Locator
  readonly newButton: Locator
  readonly emptyState: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Sequences' })
    this.newButton = page.getByRole('button', { name: '+ New Sequence' })
    this.emptyState = page.getByText('No sequences found. Create one to get started.')
  }

  async goto(): Promise<void> {
    await this.page.goto('/sequences')
  }

  row(name: string): Locator {
    return this.page.getByRole('row').filter({ hasText: name })
  }

  nameLink(name: string): Locator {
    return this.page.getByRole('link', { name })
  }

  editButtonFor(name: string): Locator {
    return this.row(name).getByTitle('Edit')
  }

  deleteButtonFor(name: string): Locator {
    return this.row(name).getByTitle('Delete')
  }

  /** Wait for the loading spinner to clear before making assertions. */
  async waitForLoaded(): Promise<void> {
    await this.page.waitForFunction(() =>
      !Array.from(document.querySelectorAll('td')).some(
        (td) => td.textContent?.trim() === 'Loading\u2026',
      ),
    )
  }

  async rowCount(): Promise<number> {
    await this.waitForLoaded()
    // Count data rows by role — works whether or not the user is authenticated
    // (auth-gated edit/delete buttons are absent for unauthenticated users).
    const allRows = await this.page.getByRole('row').count()
    // Subtract 1 for the header row; if only a state cell row is present, return 0.
    const stateRow = this.page.getByRole('cell', {
      name: 'No sequences found. Create one to get started.',
    })
    if (await stateRow.isVisible()) return 0
    return Math.max(0, allRows - 1)
  }
}
