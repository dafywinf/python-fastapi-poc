import type { components } from '../api/generated/schema'

type GeneratedActionCreate = components['schemas']['ActionCreate']
type GeneratedActionResponse = components['schemas']['ActionResponse']
type GeneratedActionUpdate = components['schemas']['ActionUpdate']
type GeneratedExecutionResponse = components['schemas']['ExecutionResponse']
type GeneratedActiveExecutionResponse = components['schemas']['ActiveExecutionResponse']
type GeneratedActionExecutionResponse = components['schemas']['ActionExecutionResponse']
type GeneratedRoutineCreate = components['schemas']['RoutineCreate']
type GeneratedRoutineResponse = components['schemas']['RoutineResponse']
type GeneratedRoutineUpdate = components['schemas']['RoutineUpdate']

export type ScheduleType = GeneratedRoutineCreate['schedule_type']
export type ScheduleConfig = { cron: string } | { seconds: number }
export type ActionType = GeneratedActionCreate['action_type']
export type ActionConfig = { message: string } | { seconds: number }

export type Action = Omit<
  GeneratedActionResponse,
  'action_type' | 'config'
> & {
  action_type: ActionType
  config: ActionConfig
}

export type Routine = Omit<
  GeneratedRoutineResponse,
  'schedule_type' | 'schedule_config' | 'actions'
> & {
  schedule_type: ScheduleType
  schedule_config: ScheduleConfig | null
  actions: Action[]
}

export type ExecutionTrigger = 'cron' | 'interval' | 'manual'
export type ActionExecutionStatus = 'pending' | 'running' | 'completed' | 'failed'

export type RoutineExecutionStatus = 'queued' | 'running' | 'completed' | 'failed'

export type RoutineExecution = Omit<
  GeneratedExecutionResponse,
  'status' | 'triggered_by' | 'started_at'
> & {
  status: RoutineExecutionStatus
  triggered_by: ExecutionTrigger
  queued_at: string
  scheduled_for: string
  started_at: string | null
}

export type ActionExecution = Omit<
  GeneratedActionExecutionResponse,
  'action_type' | 'config' | 'status'
> & {
  action_type: ActionType
  config: ActionConfig
  status: ActionExecutionStatus
}

export type ActiveRoutineExecution = Omit<
  GeneratedActiveExecutionResponse,
  'status' | 'triggered_by' | 'action_executions' | 'started_at'
> & {
  status: RoutineExecutionStatus
  triggered_by: ExecutionTrigger
  queued_at: string
  scheduled_for: string
  started_at: string | null
  action_executions: ActionExecution[]
}

export type RoutineCreate = Omit<
  GeneratedRoutineCreate,
  'schedule_config' | 'is_active'
> & {
  schedule_config?: ScheduleConfig | null
  is_active?: boolean
}

export type RoutineUpdate = Omit<
  GeneratedRoutineUpdate,
  'name' | 'schedule_type' | 'schedule_config' | 'is_active'
> & {
  name?: string
  schedule_type?: ScheduleType
  schedule_config?: ScheduleConfig | null
  is_active?: boolean
}

export type StagedAction = {
  id: number | null // null = new, not yet persisted
  action_type: ActionType
  config: ActionConfig
  position: number
  _key: string // stable key for v-for (id can be null for new actions)
}

export type ActionCreate = Omit<GeneratedActionCreate, 'config' | 'position'> & {
  config: ActionConfig
  position?: number
}

export type ActionUpdate = Omit<
  GeneratedActionUpdate,
  'action_type' | 'config' | 'position'
> & {
  action_type?: ActionType
  config?: ActionConfig
  position?: number
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}
