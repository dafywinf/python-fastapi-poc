import pluginVue from 'eslint-plugin-vue'
import eslintConfigPrettier from 'eslint-config-prettier'
import {
  defineConfigWithVueTs,
  vueTsConfigs,
} from '@vue/eslint-config-typescript'

export default defineConfigWithVueTs(
  {
    ignores: [
      'dist/',
      'node_modules/',
      '.vite/',
      'allure-results/',
      'allure-results-e2e/',
      'allure-report/',
      'allure-report-e2e/',
      'allure-report-vitest/',
      'coverage/',
      'playwright-report/',
      'playwright/.cache/',
      'test-results/',
      // Build tool configs live outside src/ and are not part of the app
      '*.config.*',
    ],
  },
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  eslintConfigPrettier,
  {
    rules: {
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports' },
      ],
      'vue/multi-word-component-names': 'off',
      'vue/attribute-hyphenation': 'off',
    },
  },
)
