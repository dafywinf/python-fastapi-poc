import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    environment: 'jsdom',
    globals: true,
    reporters: [
      'default',
      ['allure-vitest/reporter', { resultsDir: './allure-results' }],
    ],
    setupFiles: ['allure-vitest/setup', './src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,vue}'],
      exclude: ['src/main.ts', 'src/router/**', 'src/**/*.d.ts'],
    },
  },
})
