import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    reporters: ['default', ['allure-vitest/reporter', { resultsDir: './allure-results' }]],
    setupFiles: ['allure-vitest/setup'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,vue}'],
      exclude: ['src/main.ts', 'src/router/**', 'src/**/*.d.ts'],
    },
  },
})
