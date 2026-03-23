import type { components } from '../api/generated/schema'

type GeneratedActionCreate = components['schemas']['ActionCreate']
type GeneratedActionResponse = components['schemas']['ActionResponse']
type GeneratedActionUpdate = components['schemas']['ActionUpdate']
type GeneratedExecutionResponse = components['schemas']['ExecutionResponse']
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

export type RoutineExecution = Omit<
  GeneratedExecutionResponse,
  'status' | 'triggered_by'
> & {
  status: 'running' | 'completed' | 'failed'
  triggered_by: ExecutionTrigger
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
