<script setup lang="ts">
import Tag from 'primevue/tag'

type MetadataItem =
  | {
      label: string
      kind: 'text'
      value: string
      className?: string
    }
  | {
      label: string
      kind: 'schedule'
      scheduleType: 'manual' | 'cron' | 'interval'
      summary: string | null
    }

defineProps<{
  items: MetadataItem[]
}>()
</script>

<template>
  <dl class="flex flex-col border border-app-border rounded-lg overflow-hidden m-0">
    <div
      v-for="item in items"
      :key="item.label"
      class="grid grid-cols-[140px_1fr] border-b border-app-border/60 px-5 py-3.5 last:border-b-0"
    >
      <dt class="text-xs font-semibold text-slate-500 uppercase tracking-wide">
        {{ item.label }}
      </dt>
      <dd class="text-sm m-0">
        <template v-if="item.kind === 'text'">
          <span :class="item.className">{{ item.value }}</span>
        </template>
        <template v-else-if="item.kind === 'schedule'">
          <div class="text-sm text-app-text m-0 flex items-center gap-2 flex-wrap">
            <Tag
              :value="item.scheduleType"
              :severity="
                item.scheduleType === 'cron'
                  ? 'primary'
                  : item.scheduleType === 'interval'
                    ? 'info'
                    : 'secondary'
              "
            />
            <span v-if="item.summary" class="text-xs text-slate-500">
              {{ item.summary }}
            </span>
          </div>
        </template>
      </dd>
    </div>
  </dl>
</template>
