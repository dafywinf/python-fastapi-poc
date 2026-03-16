import { type Page, type Locator } from '@playwright/test'

export class FormDialog {
  readonly dialog: Locator
  readonly nameInput: Locator
  readonly saveButton: Locator
  readonly cancelButton: Locator

  constructor(page: Page) {
    this.dialog = page.getByRole('dialog')
    this.nameInput = this.dialog.getByLabel('Name *')
    this.saveButton = this.dialog.getByRole('button', { name: 'Save' })
    this.cancelButton = this.dialog.getByRole('button', { name: 'Cancel' })
  }

  async fill(name: string, description?: string): Promise<void> {
    await this.nameInput.fill(name)
    if (description !== undefined) {
      await this.dialog.getByLabel('Description').fill(description)
    }
  }

  async submit(): Promise<void> {
    await this.saveButton.click()
  }
}

export class DeleteDialog {
  readonly dialog: Locator
  readonly confirmButton: Locator
  readonly cancelButton: Locator

  constructor(page: Page) {
    this.dialog = page.getByRole('dialog')
    this.confirmButton = this.dialog.getByRole('button', { name: 'Delete' })
    this.cancelButton = this.dialog.getByRole('button', { name: 'Cancel' })
  }

  async confirm(): Promise<void> {
    await this.confirmButton.click()
  }
}
