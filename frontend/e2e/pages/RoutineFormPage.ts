import type { Locator, Page } from '@playwright/test'

export class RoutineFormPage {
  private readonly page: Page
  readonly nameInput: Locator
  readonly descriptionInput: Locator
  readonly saveButton: Locator
  readonly createButton: Locator
  readonly cancelButton: Locator
  readonly loadingSpinner: Locator
  readonly pageError: Locator

  constructor(page: Page) {
    this.page = page
    this.nameInput = page.getByPlaceholder('Enter name')
    this.descriptionInput = page.getByPlaceholder('Optional description')
    this.saveButton = page.getByRole('button', { name: 'Save' }).first()
    this.createButton = page.getByRole('button', { name: 'Create' }).first()
    this.cancelButton = page.getByRole('button', { name: 'Cancel' }).first()
    this.loadingSpinner = page.getByTestId('routine-form-loading')
    this.pageError = page.getByTestId('routine-form-page-error')
  }

  async gotoCreate(): Promise<void> {
    await this.page.goto('/routines/new')
  }

  async gotoEdit(routineId: number): Promise<void> {
    await this.page.goto(`/routines/${routineId}/edit`)
  }
}
