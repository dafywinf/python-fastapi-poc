import { type Page, type Locator } from '@playwright/test'

export class SequenceDetailPage {
  private readonly page: Page
  readonly backLink: Locator
  readonly editButton: Locator
  readonly deleteButton: Locator

  constructor(page: Page) {
    this.page = page
    this.backLink = page.getByRole('link', { name: '← Back to Sequences' })
    this.editButton = page.getByRole('button', { name: 'Edit' })
    this.deleteButton = page.getByRole('button', { name: 'Delete' })
  }

  async goto(id: number): Promise<void> {
    await this.page.goto(`/sequences/${id}`)
  }

  heading(name: string): Locator {
    return this.page.getByRole('heading', { name })
  }
}
