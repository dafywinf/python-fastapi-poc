import { expect, test } from '@playwright/experimental-ct-vue'
import type { ActiveRoutineExecution } from '../src/types/routine'
import ExecutionCard from '../src/features/routines/components/ExecutionCard.vue'

const runningExecution: ActiveRoutineExecution = {
  id: 1,
  routine_id: 10,
  routine_name: 'Morning Routine',
  status: 'running',
  triggered_by: 'manual',
  queued_at: '2026-01-01T08:00:00Z',
  scheduled_for: '2026-01-01T08:00:00Z',
  started_at: '2026-01-01T08:00:01Z',
  completed_at: null,
  action_executions: [
    {
      id: 1,
      action_id: 1,
      position: 1,
      action_type: 'echo',
      config: { message: 'hello' },
      status: 'completed',
      started_at: '2026-01-01T08:00:01Z',
      completed_at: '2026-01-01T08:00:02Z',
    },
    {
      id: 2,
      action_id: 2,
      position: 2,
      action_type: 'sleep',
      config: { seconds: 5 },
      status: 'running',
      started_at: '2026-01-01T08:00:02Z',
      completed_at: null,
    },
  ],
}

const queuedExecution: ActiveRoutineExecution = {
  id: 2,
  routine_id: 10,
  routine_name: 'Evening Routine',
  status: 'queued',
  triggered_by: 'manual',
  queued_at: '2026-01-01T08:00:00Z',
  scheduled_for: '2026-01-01T08:00:00Z',
  started_at: null,
  completed_at: null,
  action_executions: [],
}

const completedExecution: ActiveRoutineExecution = {
  id: 3,
  routine_id: 10,
  routine_name: 'Backup Routine',
  status: 'completed',
  triggered_by: 'cron',
  queued_at: '2026-01-01T07:00:00Z',
  scheduled_for: '2026-01-01T07:00:00Z',
  started_at: '2026-01-01T07:00:01Z',
  completed_at: '2026-01-01T07:00:10Z',
  action_executions: [],
}

const failedExecution: ActiveRoutineExecution = {
  id: 4,
  routine_id: 10,
  routine_name: 'Nightly Sync',
  status: 'failed',
  triggered_by: 'cron',
  queued_at: '2026-01-01T03:00:00Z',
  scheduled_for: '2026-01-01T03:00:00Z',
  started_at: '2026-01-01T03:00:01Z',
  completed_at: '2026-01-01T03:00:05Z',
  action_executions: [],
}

test.describe('ExecutionCard', () => {
  test('renders a running execution with routine name and running tag', async ({ mount }) => {
    const component = await mount(ExecutionCard, {
      props: { execution: runningExecution },
    })

    const header = component.getByTestId('execution-card-header')
    await expect(header).toBeVisible()
    await expect(header.getByText('Morning Routine')).toBeVisible()
    await expect(header.getByText('running', { exact: true })).toBeVisible()
  })

  test('auto-expands a running execution and shows action rows', async ({ mount }) => {
    const component = await mount(ExecutionCard, {
      props: { execution: runningExecution },
    })

    // Running cards start expanded — action rows should be immediately visible
    await expect(component.getByText('echo')).toBeVisible()
    await expect(component.getByText('sleep')).toBeVisible()
  })

  test('renders a queued execution with position badge and queued tag', async ({ mount }) => {
    const component = await mount(ExecutionCard, {
      props: { execution: queuedExecution, queuePosition: 2 },
    })

    await expect(component.getByTestId('execution-card-header')).toBeVisible()
    await expect(component.getByText('Evening Routine')).toBeVisible()
    await expect(component.getByText('queued', { exact: true })).toBeVisible()
    await expect(component.getByText('#2')).toBeVisible()
  })

  test('renders a completed execution with correct status tag', async ({ mount }) => {
    const component = await mount(ExecutionCard, {
      props: { execution: completedExecution },
    })

    await expect(component.getByText('Backup Routine')).toBeVisible()
    await expect(component.getByText('completed')).toBeVisible()
  })

  test('renders a failed execution with correct status tag', async ({ mount }) => {
    const component = await mount(ExecutionCard, {
      props: { execution: failedExecution },
    })

    await expect(component.getByText('Nightly Sync')).toBeVisible()
    await expect(component.getByText('failed')).toBeVisible()
  })

  test('shows loading state in expanded body when detailLoading is true', async ({ mount }) => {
    const component = await mount(ExecutionCard, {
      props: { execution: runningExecution, detailLoading: true },
    })

    // Running card is auto-expanded, so the loading indicator should be visible
    await expect(component.getByText('Loading…')).toBeVisible()
  })

  test('shows error state in expanded body when detailError is true', async ({ mount }) => {
    const component = await mount(ExecutionCard, {
      props: { execution: completedExecution, detailError: true },
    })

    // Click the header to expand the completed card
    await component.getByTestId('execution-card-header').click()
    await expect(component.getByText('Failed to load action details')).toBeVisible()
  })
})
