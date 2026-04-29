import type { Locator, Page } from '@playwright/test'

export class ActiveExecutionsPage {
  private readonly page: Page
  readonly heading: Locator
  readonly emptyMessage: Locator
  readonly errorBanner: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Execution Queue' })
    this.emptyMessage = page.getByTestId('execution-queue-empty')
    this.errorBanner = page.getByTestId('execution-queue-error')
  }

  async goto(): Promise<void> {
    await this.page.goto('/executing')
  }

  executionCard(routineName: string): Locator {
    return this.page.getByText(routineName)
  }
}
