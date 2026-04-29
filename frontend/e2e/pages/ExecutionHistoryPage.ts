import type { Locator, Page } from '@playwright/test'

export class ExecutionHistoryPage {
  private readonly page: Page
  readonly heading: Locator
  readonly list: Locator
  readonly emptyMessage: Locator
  readonly errorBanner: Locator
  readonly searchInput: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Execution History' })
    this.list = page.getByTestId('history-list')
    this.emptyMessage = page.getByTestId('history-empty')
    this.errorBanner = page.getByTestId('history-error')
    this.searchInput = page.getByPlaceholder('Filter by routine name…')
  }

  async goto(): Promise<void> {
    await this.page.goto('/history')
  }
}
