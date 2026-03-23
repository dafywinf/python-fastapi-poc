<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-1">
      <label :for="`${idPrefix}-name`" class="text-sm font-medium text-slate-700"
        >Name</label
      >
      <InputText
        :id="`${idPrefix}-name`"
        v-model="nameModel"
        :input-id="`${idPrefix}-name`"
        :invalid="!!errors?.name"
        placeholder="Enter name"
        required
      />
      <small v-if="errors?.name" class="text-red-600">{{ errors.name }}</small>
    </div>

    <div class="flex flex-col gap-1">
      <label
        :for="`${idPrefix}-description`"
        class="text-sm font-medium text-slate-700"
        >Description</label
      >
      <Textarea
        :id="`${idPrefix}-description`"
        v-model="descriptionModel"
        rows="3"
        placeholder="Optional description"
      />
    </div>

    <div class="flex flex-col gap-1">
      <label
        :for="`${idPrefix}-schedule-type`"
        class="text-sm font-medium text-slate-700"
        >Schedule Type</label
      >
      <Select
        :id="`${idPrefix}-schedule-type`"
        v-model="scheduleTypeModel"
        :options="scheduleOptions"
        option-label="label"
        option-value="value"
        class="w-full"
      />
    </div>

    <div v-if="scheduleTypeModel === 'cron'" class="flex flex-col gap-1">
      <label :for="`${idPrefix}-cron`" class="text-sm font-medium text-slate-700"
        >Cron Expression</label
      >
      <InputText
        :id="`${idPrefix}-cron`"
        v-model="cronExpressionModel"
        :invalid="!!errors?.cronExpression"
        placeholder="e.g. 0 * * * *"
      />
      <small v-if="errors?.cronExpression" class="text-red-600">{{
        errors.cronExpression
      }}</small>
    </div>

    <div v-if="scheduleTypeModel === 'interval'" class="flex flex-col gap-1">
      <label
        :for="`${idPrefix}-interval`"
        class="text-sm font-medium text-slate-700"
        >Interval (seconds)</label
      >
      <InputText
        :id="`${idPrefix}-interval`"
        v-model="intervalSecondsModel"
        type="number"
        :invalid="!!errors?.intervalSeconds"
        min="1"
        placeholder="e.g. 60"
      />
      <small v-if="errors?.intervalSeconds" class="text-red-600">{{
        errors.intervalSeconds
      }}</small>
    </div>

    <div class="flex items-center gap-2">
      <Checkbox
        v-model="isActiveModel"
        :binary="true"
        :input-id="`${idPrefix}-active`"
      />
      <label :for="`${idPrefix}-active`" class="text-sm text-slate-700"
        >Active</label
      >
    </div>
  </div>
</template>

<script setup lang="ts">
import Checkbox from 'primevue/checkbox'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'

type ScheduleType = 'manual' | 'cron' | 'interval'

defineProps<{
  idPrefix: string
  errors?: {
    name?: string
    cronExpression?: string
    intervalSeconds?: string
  }
}>()

const nameModel = defineModel<string | undefined>('name', { required: true })
const descriptionModel = defineModel<string | null | undefined>('description', {
  required: true,
})
const scheduleTypeModel = defineModel<ScheduleType | undefined>('scheduleType', {
  required: true,
})
const cronExpressionModel = defineModel<string>('cronExpression', {
  required: true,
})
const intervalSecondsModel = defineModel<string>('intervalSeconds', {
  required: true,
})
const isActiveModel = defineModel<boolean | undefined>('isActive', {
  required: true,
})

const scheduleOptions = [
  { label: 'manual', value: 'manual' },
  { label: 'cron', value: 'cron' },
  { label: 'interval', value: 'interval' },
]
</script>
