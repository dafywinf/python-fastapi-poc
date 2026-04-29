import type { Locator, Page } from '@playwright/test'

export class RoutinesPage {
  private readonly page: Page
  readonly heading: Locator
  readonly newButton: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Routines' })
    this.newButton = page.getByRole('button', { name: '+ New Routine' })
  }

  async goto(): Promise<void> {
    await this.page.goto('/routines')
  }

  row(name: string): Locator {
    return this.page.getByTestId('routines-table').getByRole('row').filter({ hasText: name })
  }
}
