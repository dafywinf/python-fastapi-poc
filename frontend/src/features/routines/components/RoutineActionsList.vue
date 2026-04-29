<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { VueDraggable } from 'vue-draggable-plus'
import type { StagedAction } from '../../../types/routine'

const props = defineProps<{
  actions: StagedAction[]
  editable: boolean
  summarizeConfig: (action: StagedAction) => string
}>()

const emit = defineEmits<{
  reorder: [actions: StagedAction[]]
  remove: [action: StagedAction]
}>()

// Local copy for drag-and-drop; kept in sync with props when not dragging.
const localActions = ref<StagedAction[]>([...props.actions])

watch(
  () => props.actions,
  (next) => {
    localActions.value = [...next]
  },
)

function onDragEnd(): void {
  emit('reorder', localActions.value)
}
</script>

<template>
  <div
    v-if="actions.length"
    class="flex flex-col border border-app-border rounded-lg overflow-hidden"
  >
    <VueDraggable
      v-if="editable"
      v-model="localActions"
      handle=".drag-handle"
      :animation="150"
      @end="onDragEnd"
    >
      <div
        v-for="action in localActions"
        :key="action._key"
        class="flex items-center gap-3 px-4 py-3 border-b border-app-border/60 last:border-b-0 hover:bg-slate-50"
      >
        <span
          class="drag-handle material-symbols-outlined text-app-muted text-lg cursor-grab active:cursor-grabbing select-none shrink-0"
          title="Drag to reorder"
        >
          drag_indicator
        </span>
        <span
          class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-app-muted min-w-7 text-center"
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
        <Button
          label="Remove"
          size="small"
          severity="danger"
          title="Remove action"
          @click="emit('remove', action)"
        />
      </div>
    </VueDraggable>

    <!-- Read-only (non-edit mode) -->
    <template v-else>
      <div
        v-for="action in actions"
        :key="action._key"
        class="flex items-center gap-3 px-4 py-3 border-b border-app-border/60 last:border-b-0"
      >
        <span
          class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-app-muted min-w-7 text-center"
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
      </div>
    </template>
  </div>
</template>
