import type { Locator, Page } from '@playwright/test'

export class RoutineDetailPage {
  private readonly page: Page
  readonly loadingSpinner: Locator
  readonly errorBanner: Locator
  readonly header: Locator
  readonly runButton: Locator
  readonly editButton: Locator
  readonly deleteButton: Locator

  constructor(page: Page) {
    this.page = page
    this.loadingSpinner = page.getByTestId('routine-detail-loading')
    this.errorBanner = page.getByTestId('routine-detail-error')
    this.header = page.getByTestId('routine-detail-header')
    this.runButton = page.getByRole('button', { name: '▶ Run Now' })
    this.editButton = page.getByRole('button', { name: 'Edit' })
    this.deleteButton = page.getByRole('button', { name: 'Delete' })
  }

  async goto(routineId: number): Promise<void> {
    await this.page.goto(`/routines/${routineId}`)
  }
}
