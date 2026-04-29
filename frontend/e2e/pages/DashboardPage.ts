import type { Locator, Page } from '@playwright/test'

export class DashboardPage {
  private readonly page: Page
  readonly heading: Locator
  readonly queuePanel: Locator
  readonly historyPanel: Locator
  readonly routinesPanel: Locator
  readonly emptyQueue: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Execution Dashboard' })
    this.queuePanel = page.getByTestId('dashboard-queue-panel')
    this.historyPanel = page.getByTestId('dashboard-history-panel')
    this.routinesPanel = page.getByTestId('dashboard-routines-panel')
    this.emptyQueue = page.getByTestId('execution-queue-empty')
  }

  async goto(): Promise<void> {
    await this.page.goto('/')
  }
}
