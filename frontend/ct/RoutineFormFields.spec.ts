import { expect, test } from '@playwright/experimental-ct-vue'
import RoutineFormFields from '../src/features/routines/components/RoutineFormFields.vue'

const baseProps = {
  idPrefix: 'test',
  name: 'My Routine',
  description: null,
  scheduleType: 'manual' as const,
  cronExpression: '',
  intervalSeconds: '',
  isActive: true,
}

test.describe('RoutineFormFields', () => {
  test('renders name, description, schedule type and active fields', async ({ mount }) => {
    const component = await mount(RoutineFormFields, { props: baseProps })

    await expect(component.getByPlaceholder('Enter name')).toBeVisible()
    await expect(component.getByPlaceholder('Optional description')).toBeVisible()
    await expect(component.getByText('Schedule Type')).toBeVisible()
    await expect(component.getByText('Active', { exact: true })).toBeVisible()
  })

  test('shows cron expression field when schedule type is cron', async ({ mount }) => {
    const component = await mount(RoutineFormFields, {
      props: { ...baseProps, scheduleType: 'cron' as const },
    })

    await expect(component.getByTestId('form-cron-field')).toBeVisible()
    await expect(component.getByPlaceholder('e.g. 0 * * * *')).toBeVisible()
    await expect(component.getByTestId('form-interval-field')).not.toBeVisible()
  })

  test('shows interval field when schedule type is interval', async ({ mount }) => {
    const component = await mount(RoutineFormFields, {
      props: { ...baseProps, scheduleType: 'interval' as const },
    })

    await expect(component.getByTestId('form-interval-field')).toBeVisible()
    await expect(component.getByPlaceholder('e.g. 60')).toBeVisible()
    await expect(component.getByTestId('form-cron-field')).not.toBeVisible()
  })

  test('hides cron and interval fields when schedule type is manual', async ({ mount }) => {
    const component = await mount(RoutineFormFields, { props: baseProps })

    await expect(component.getByTestId('form-cron-field')).not.toBeVisible()
    await expect(component.getByTestId('form-interval-field')).not.toBeVisible()
  })

  test('shows name validation error when error prop is set', async ({ mount }) => {
    const component = await mount(RoutineFormFields, {
      props: { ...baseProps, errors: { name: 'Name is required' } },
    })

    await expect(component.getByTestId('form-name-error')).toBeVisible()
    await expect(component.getByText('Name is required')).toBeVisible()
  })

  test('shows cron validation error when error prop is set', async ({ mount }) => {
    const component = await mount(RoutineFormFields, {
      props: {
        ...baseProps,
        scheduleType: 'cron' as const,
        errors: { cronExpression: 'Invalid cron expression' },
      },
    })

    await expect(component.getByText('Invalid cron expression')).toBeVisible()
  })
})
