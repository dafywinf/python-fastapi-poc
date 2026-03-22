export interface Routine {
  id: number
  name: string
  description: string | null
  schedule_type: 'cron' | 'interval' | 'manual'
  schedule_config: { cron: string } | { seconds: number } | null
  is_active: boolean
  created_at: string
  actions: Action[]
}

export interface Action {
  id: number
  routine_id: number
  position: number
  action_type: 'sleep' | 'echo'
  config: { seconds: number } | { message: string }
}

export interface RoutineExecution {
  id: number
  routine_id: number
  routine_name: string
  status: 'running' | 'completed' | 'failed'
  triggered_by: 'cron' | 'interval' | 'manual'
  started_at: string
  completed_at: string | null
}

export interface RoutineCreate {
  name: string
  description?: string | null
  schedule_type: 'cron' | 'interval' | 'manual'
  schedule_config?: { cron: string } | { seconds: number } | null
  is_active?: boolean
}

export interface RoutineUpdate {
  name?: string
  description?: string | null
  schedule_type?: 'cron' | 'interval' | 'manual'
  schedule_config?: { cron: string } | { seconds: number } | null
  is_active?: boolean
}

export interface ActionCreate {
  action_type: 'sleep' | 'echo'
  config: { seconds: number } | { message: string }
  position?: number
}

export interface ActionUpdate {
  action_type?: 'sleep' | 'echo'
  config?: { seconds: number } | { message: string }
  position?: number
}
