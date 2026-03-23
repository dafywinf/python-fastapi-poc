<template>
  <div
    v-if="actions.length"
    class="flex flex-col border border-slate-200 rounded-lg overflow-hidden"
  >
    <div
      v-for="action in actions"
      :key="action.id"
      class="flex items-center gap-3 px-4 py-3 border-b border-slate-100 last:border-b-0 hover:bg-slate-50"
    >
      <span
        class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 min-w-7 text-center"
      >
        {{ action.position }}
      </span>
      <Tag
        :value="action.action_type"
        :severity="action.action_type === 'sleep' ? 'info' : 'primary'"
      />
      <span class="flex-1 text-sm text-slate-500">
        {{ summarizeConfig(action) }}
      </span>
      <div v-if="editable" class="flex gap-1.5 shrink-0">
        <Button
          label="▲"
          size="small"
          severity="secondary"
          :disabled="action.position === 1"
          title="Move up"
          @click="emit('move', action, 'up')"
        />
        <Button
          label="▼"
          size="small"
          severity="secondary"
          :disabled="action.position === actions.length"
          title="Move down"
          @click="emit('move', action, 'down')"
        />
        <Button
          label="Delete"
          size="small"
          severity="danger"
          title="Delete action"
          @click="emit('remove', action)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import type { Action } from '../../../types/routine'

defineProps<{
  actions: Action[]
  editable: boolean
  summarizeConfig: (action: Action) => string
}>()

const emit = defineEmits<{
  move: [action: Action, direction: 'up' | 'down']
  remove: [action: Action]
}>()
</script>
