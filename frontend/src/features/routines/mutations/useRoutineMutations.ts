import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { routinesApi } from '../../../api/routines'
import type { RoutineCreate, RoutineUpdate } from '../../../types/routine'
import { routineKeys } from '../queries/keys'

async function invalidateRoutineList(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  await queryClient.invalidateQueries({ queryKey: routineKeys.all })
}

async function invalidateExecutionQueries(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  await queryClient.invalidateQueries({ queryKey: routineKeys.executions })
}

async function invalidateRoutineDetail(
  queryClient: ReturnType<typeof useQueryClient>,
  routineId: number,
) {
  await queryClient.invalidateQueries({
    queryKey: routineKeys.detail(routineId),
  })
}

export function useCreateRoutineMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: RoutineCreate) => routinesApi.create(payload),
    onSuccess: async () => {
      await invalidateRoutineList(queryClient)
    },
  })
}

export function useUpdateRoutineMutation(routineId?: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: RoutineUpdate }) =>
      routinesApi.update(id, payload),
    onSuccess: async (_, variables) => {
      await invalidateRoutineList(queryClient)
      await invalidateRoutineDetail(queryClient, routineId ?? variables.id)
    },
  })
}

export function useDeleteRoutineMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (routineId: number) => routinesApi.delete(routineId),
    onSuccess: async () => {
      await invalidateRoutineList(queryClient)
    },
  })
}

export function useRunRoutineMutation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (routineId: number) => routinesApi.runNow(routineId),
    onSuccess: async () => {
      await invalidateExecutionQueries(queryClient)
    },
  })
}

export function useCreateActionMutation(routineId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: {
      action_type: 'echo' | 'sleep'
      config: { message: string } | { seconds: number }
    }) => routinesApi.createAction(routineId, payload),
    onSuccess: async () => {
      await invalidateRoutineDetail(queryClient, routineId)
    },
  })
}

export function useReorderActionMutation(routineId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      actionId,
      position,
    }: {
      actionId: number
      position: number
    }) => routinesApi.updateAction(actionId, { position }),
    onSuccess: async () => {
      await invalidateRoutineDetail(queryClient, routineId)
    },
  })
}

export function useDeleteActionMutation(routineId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (actionId: number) => routinesApi.deleteAction(actionId),
    onSuccess: async () => {
      await invalidateRoutineDetail(queryClient, routineId)
    },
  })
}
