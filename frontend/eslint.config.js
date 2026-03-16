import pluginVue from 'eslint-plugin-vue'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'

export default defineConfigWithVueTs(
  {
    ignores: [
      'dist/',
      'node_modules/',
      '.vite/',
      'allure-results/',
      'allure-results-e2e/',
      'allure-report/',
      'coverage/',
      'playwright-report/',
      'test-results/',
      // Build tool configs live outside src/ and are not part of the app
      '*.config.*',
    ],
  },
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  {
    rules: {
      // Enforce type-only imports — consistent with the TypeScript Pro standard
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],

      // ── Disable HTML formatting rules ────────────────────────────────────
      // These are style preferences, not correctness issues. Formatting is
      // handled by the developer; we do not run Prettier in this project.
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/multiline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
    },
  },
)
