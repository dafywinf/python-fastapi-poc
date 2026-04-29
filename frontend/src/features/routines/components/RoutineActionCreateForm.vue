<script setup lang="ts">
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

defineProps<{
  idPrefix: string
  submitting: boolean
  configError?: string | null
}>()

const actionTypeModel = defineModel<'echo' | 'sleep'>('actionType', {
  required: true,
})
const echoMessageModel = defineModel<string>('echoMessage', {
  required: true,
})
const sleepSecondsModel = defineModel<string>('sleepSeconds', {
  required: true,
})

const emit = defineEmits<{
  'type-change': []
  submit: []
}>()

const actionOptions = [
  { label: 'echo', value: 'echo' },
  { label: 'sleep', value: 'sleep' },
]
</script>

<template>
  <div class="border border-app-border rounded-lg p-4 flex flex-col gap-3">
    <h3 class="text-sm font-semibold text-app-text m-0">Add Action</h3>
    <div class="flex items-end gap-3 flex-wrap">
      <div class="flex flex-col gap-1 flex-1 min-w-36">
        <label class="text-sm font-medium text-slate-700" :for="`${idPrefix}-type`"
          >Type</label
        >
        <Select
          :id="`${idPrefix}-type`"
          v-model="actionTypeModel"
          :options="actionOptions"
          option-label="label"
          option-value="value"
          class="w-full"
          @change="emit('type-change')"
        />
      </div>
      <div class="flex flex-col gap-1 flex-1 min-w-36">
        <label class="text-sm font-medium text-slate-700" :for="`${idPrefix}-config`">
          {{ actionTypeModel === 'echo' ? 'Message' : 'Seconds' }}
        </label>
        <InputText
          v-if="actionTypeModel === 'echo'"
          :id="`${idPrefix}-config`"
          v-model="echoMessageModel"
          :invalid="!!configError"
          placeholder="Enter message"
        />
        <InputText
          v-else
          :id="`${idPrefix}-config`"
          v-model="sleepSecondsModel"
          type="number"
          :invalid="!!configError"
          min="1"
          placeholder="e.g. 5"
        />
      </div>
      <Button
        :label="submitting ? 'Adding…' : 'Add'"
        :disabled="submitting"
        class="shrink-0 self-end mb-0"
        @click="emit('submit')"
      />
    </div>
    <small v-if="configError" class="text-red-600">{{ configError }}</small>
  </div>
</template>
