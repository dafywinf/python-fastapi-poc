import type { Locator, Page } from '@playwright/test'

export class UsersPage {
  private readonly page: Page
  readonly heading: Locator
  readonly tableContainer: Locator
  readonly emptyMessage: Locator
  readonly errorBanner: Locator

  constructor(page: Page) {
    this.page = page
    this.heading = page.getByRole('heading', { name: 'Users' })
    this.tableContainer = page.getByTestId('users-table-container')
    this.emptyMessage = page.getByTestId('users-empty')
    this.errorBanner = page.getByTestId('users-error')
  }

  async goto(): Promise<void> {
    await this.page.goto('/users')
  }

  /**
   * Returns the table row containing the given user name.
   * Mirrors the RoutinesPage.row() pattern.
   */
  row(name: string): Locator {
    return this.page
      .getByTestId('users-table')
      .getByRole('row')
      .filter({ hasText: name })
  }

  /**
   * Returns the copy-email button for a specific user by database id.
   */
  copyEmailButton(userId: number): Locator {
    return this.page.getByTestId(`copy-email-${userId}`)
  }

  /**
   * Returns the name cell for a specific user by database id.
   * Useful for asserting avatar vs initials rendering.
   */
  nameCell(userId: number): Locator {
    return this.page.getByTestId(`user-name-cell-${userId}`)
  }
}
