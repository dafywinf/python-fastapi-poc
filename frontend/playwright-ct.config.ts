import { defineConfig, devices } from '@playwright/experimental-ct-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  testDir: './ct',
  timeout: 10_000,
  expect: { timeout: 5_000 },
  // allure-playwright cannot be used here: @playwright/experimental-ct-vue bundles
  // its own internal playwright, and allure-playwright's import of @playwright/test
  // triggers a "Requiring @playwright/test second time" conflict. The CT layer
  // reports to the terminal only; E2E and Vitest layers cover Allure reporting.
  reporter: [['list']],
  use: {
    ctViteConfig: {
      resolve: {
        alias: {
          '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
      },
    },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
