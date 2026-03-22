<template>
  <div class="flex flex-col gap-5 max-w-3xl">
    <!-- Back link -->
    <button @click="router.back()" class="text-sm text-indigo-600 hover:underline font-medium text-left bg-transparent border-none p-0 cursor-pointer">← Back</button>

    <div v-if="loading" class="text-slate-400 py-8 flex items-center gap-2">
      <span class="inline-block w-5 h-5 border-2 border-slate-200 border-t-indigo-500 rounded-full animate-spin" aria-label="Loading" />
    </div>
    <div v-else-if="pageError" class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200">{{ pageError }}</div>

    <template v-else-if="routine">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-semibold text-slate-900 m-0">{{ routine.name }}</h1>
        <div class="flex items-center gap-2 shrink-0">
          <Button v-if="!editing" label="Edit" severity="secondary" @click="startEdit" />
          <Button
            v-if="isAuthenticated"
            :label="runNowLoading ? '…' : '▶ Run Now'"
            :disabled="runNowLoading"
            @click="runNow"
          />
        </div>
      </div>

      <!-- Metadata: read-only -->
      <template v-if="!editing">
        <dl class="flex flex-col border border-slate-200 rounded-lg overflow-hidden m-0">
          <div class="grid border-b border-slate-100 px-5 py-3.5" style="grid-template-columns: 140px 1fr">
            <dt class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Name</dt>
            <dd class="text-sm text-slate-900 m-0">{{ routine.name }}</dd>
          </div>
          <div class="grid border-b border-slate-100 px-5 py-3.5" style="grid-template-columns: 140px 1fr">
            <dt class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Description</dt>
            <dd class="text-sm text-slate-500 m-0">{{ routine.description ?? '—' }}</dd>
          </div>
          <div class="grid border-b border-slate-100 px-5 py-3.5" style="grid-template-columns: 140px 1fr">
            <dt class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Schedule</dt>
            <dd class="text-sm text-slate-900 m-0 flex items-center gap-2 flex-wrap">
              <Tag
                :value="routine.schedule_type"
                :severity="routine.schedule_type === 'cron' ? 'primary' : routine.schedule_type === 'interval' ? 'info' : 'secondary'"
              />
              <span v-if="scheduleConfigSummary" class="text-xs text-slate-500">{{ scheduleConfigSummary }}</span>
            </dd>
          </div>
          <div class="grid px-5 py-3.5" style="grid-template-columns: 140px 1fr">
            <dt class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Active</dt>
            <dd class="text-sm m-0">
              <span v-if="routine.is_active" class="text-green-600 font-semibold">✓ Active</span>
              <span v-else class="text-slate-400">Inactive</span>
            </dd>
          </div>
        </dl>
      </template>

      <!-- Metadata: edit form -->
      <template v-else>
        <div class="border border-slate-200 rounded-lg p-5 flex flex-col gap-4">
          <h2 class="text-base font-semibold text-slate-900 m-0">Edit Routine</h2>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700" for="edit-name">Name *</label>
            <InputText id="edit-name" v-model="form.name" placeholder="Enter name" required />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700" for="edit-desc">Description</label>
            <Textarea id="edit-desc" v-model="form.description" rows="3" placeholder="Optional description" />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700" for="edit-schedule-type">Schedule Type</label>
            <Select
              v-model="form.schedule_type"
              :options="[{ label: 'manual', value: 'manual' }, { label: 'cron', value: 'cron' }, { label: 'interval', value: 'interval' }]"
              option-label="label"
              option-value="value"
              class="w-full"
            />
          </div>
          <div v-if="form.schedule_type === 'cron'" class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700" for="edit-cron">Cron Expression</label>
            <InputText id="edit-cron" v-model="editCronExpression" placeholder="e.g. 0 * * * *" />
          </div>
          <div v-if="form.schedule_type === 'interval'" class="flex flex-col gap-1">
            <label class="text-sm font-medium text-slate-700" for="edit-interval">Interval (seconds)</label>
            <InputText id="edit-interval" v-model="editIntervalSecondsStr" type="number" min="1" placeholder="e.g. 60" />
          </div>
          <div class="flex items-center gap-2">
            <Checkbox v-model="form.is_active" :binary="true" inputId="edit-active" />
            <label for="edit-active" class="text-sm text-slate-700">Active</label>
          </div>
          <div v-if="saveError" class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200">{{ saveError }}</div>
          <div class="flex justify-end gap-3 mt-1">
            <Button label="Cancel" severity="secondary" @click="editing = false" />
            <Button :label="saving ? 'Saving…' : 'Save'" :disabled="saving" @click="saveEdit" />
          </div>
        </div>
      </template>

      <!-- Actions section -->
      <div class="flex flex-col gap-3">
        <h2 class="text-lg font-semibold text-slate-900 m-0">Actions</h2>

        <div v-if="actionError" class="px-4 py-2.5 rounded-md text-sm bg-red-50 text-red-600 border border-red-200">{{ actionError }}</div>

        <div v-if="routine.actions.length === 0" class="text-slate-400 py-4">
          No actions yet. Add one below.
        </div>

        <div v-else class="flex flex-col border border-slate-200 rounded-lg overflow-hidden">
          <div
            v-for="action in sortedActions"
            :key="action.id"
            class="flex items-center gap-3 px-4 py-3 border-b border-slate-100 last:border-b-0 hover:bg-slate-50"
          >
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 min-w-7 text-center">
              {{ action.position }}
            </span>
            <Tag
              :value="action.action_type"
              :severity="action.action_type === 'sleep' ? 'info' : 'primary'"
            />
            <span class="flex-1 text-sm text-slate-500">{{ actionConfigSummary(action) }}</span>
            <div class="flex gap-1.5 shrink-0">
              <Button
                label="▲"
                size="small"
                severity="secondary"
                :disabled="action.position === 1"
                title="Move up"
                @click="moveAction(action, 'up')"
              />
              <Button
                label="▼"
                size="small"
                severity="secondary"
                :disabled="action.position === routine.actions.length"
                title="Move down"
                @click="moveAction(action, 'down')"
              />
              <Button
                label="Delete"
                size="small"
                severity="danger"
                title="Delete action"
                @click="removeAction(action)"
              />
            </div>
          </div>
        </div>

        <!-- Add action form -->
        <div class="border border-slate-200 rounded-lg p-4 flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-slate-900 m-0">Add Action</h3>
          <div class="flex items-end gap-3 flex-wrap">
            <div class="flex flex-col gap-1 flex-1 min-w-36">
              <label class="text-sm font-medium text-slate-700" for="action-type">Type</label>
              <Select
                v-model="actionForm.action_type"
                :options="[{ label: 'echo', value: 'echo' }, { label: 'sleep', value: 'sleep' }]"
                option-label="label"
                option-value="value"
                class="w-full"
                @change="onActionTypeChange"
              />
            </div>
            <div class="flex flex-col gap-1 flex-1 min-w-36">
              <label class="text-sm font-medium text-slate-700" for="action-config">
                {{ actionForm.action_type === 'echo' ? 'Message' : 'Seconds' }}
              </label>
              <InputText
                v-if="actionForm.action_type === 'echo'"
                id="action-config"
                v-model="echoMessage"
                placeholder="Enter message"
              />
              <InputText
                v-else
                id="action-config"
                v-model="sleepSecondsStr"
                type="number"
                min="1"
                placeholder="e.g. 5"
              />
            </div>
            <Button
              :label="addingAction ? 'Adding…' : 'Add'"
              :disabled="addingAction"
              class="shrink-0 self-end mb-0"
              @click="addAction"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { routinesApi } from '../api/routines'
import { useAuth } from '../composables/useAuth'
import type { Action, ActionCreate, Routine, RoutineUpdate } from '../types/routine'

const props = defineProps<{ id: number }>()
const toast = useToast()
const { isAuthenticated } = useAuth()

// ── Page state ─────────────────────────────────────────────────────────────
const routine = ref<Routine | null>(null)
const loading = ref(true)
const pageError = ref<string | null>(null)

// ── Edit form state ─────────────────────────────────────────────────────────
const editing = ref(false)
const form = ref<RoutineUpdate & { description?: string | null; schedule_type?: 'cron' | 'interval' | 'manual' }>({})
const saving = ref(false)
const saveError = ref<string | null>(null)

// Local schedule config helpers for edit form
const editCronExpression = ref('')
const editIntervalSeconds = ref<number>(60)
const editIntervalSecondsStr = computed({
  get: () => String(editIntervalSeconds.value),
  set: (v: string) => { editIntervalSeconds.value = parseInt(v, 10) || 60 },
})

// ── Action management ───────────────────────────────────────────────────────
const actionForm = ref<ActionCreate>({ action_type: 'echo', config: { message: '' } })
const echoMessage = ref('')
const sleepSeconds = ref<number>(5)
const sleepSecondsStr = computed({
  get: () => String(sleepSeconds.value),
  set: (v: string) => { sleepSeconds.value = parseInt(v, 10) || 5 },
})
const addingAction = ref(false)
const actionError = ref<string | null>(null)

// ── Run Now ─────────────────────────────────────────────────────────────────
const runNowLoading = ref(false)

// ── Computed ────────────────────────────────────────────────────────────────
const sortedActions = computed<Action[]>(() => {
  if (!routine.value) return []
  return [...routine.value.actions].sort((a, b) => a.position - b.position)
})

const scheduleConfigSummary = computed<string | null>(() => {
  if (!routine.value) return null
  const cfg = routine.value.schedule_config
  if (!cfg) return null
  if ('cron' in cfg) return `(${cfg.cron})`
  if ('seconds' in cfg) return `(every ${cfg.seconds}s)`
  return null
})

// ── Helpers ─────────────────────────────────────────────────────────────────
function actionConfigSummary(action: Action): string {
  const cfg = action.config
  if ('message' in cfg) return `echo: ${cfg.message}`
  if ('seconds' in cfg) return `sleep ${cfg.seconds}s`
  return ''
}

function onActionTypeChange(): void {
  if (actionForm.value.action_type === 'echo') {
    actionForm.value.config = { message: '' }
    echoMessage.value = ''
  } else {
    actionForm.value.config = { seconds: 5 }
    sleepSeconds.value = 5
  }
}

// ── Data loading ─────────────────────────────────────────────────────────────
async function load(): Promise<void> {
  loading.value = true
  pageError.value = null
  try {
    routine.value = await routinesApi.get(props.id)
  } catch {
    pageError.value = 'Routine not found'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

// ── Edit ─────────────────────────────────────────────────────────────────────
function startEdit(): void {
  if (!routine.value) return
  form.value = {
    name: routine.value.name,
    description: routine.value.description,
    schedule_type: routine.value.schedule_type,
    schedule_config: routine.value.schedule_config,
    is_active: routine.value.is_active,
  }
  // Pre-populate schedule config helpers
  if (routine.value.schedule_type === 'cron' && routine.value.schedule_config && 'cron' in routine.value.schedule_config) {
    editCronExpression.value = routine.value.schedule_config.cron
  } else {
    editCronExpression.value = ''
  }
  if (routine.value.schedule_type === 'interval' && routine.value.schedule_config && 'seconds' in routine.value.schedule_config) {
    editIntervalSeconds.value = routine.value.schedule_config.seconds
  } else {
    editIntervalSeconds.value = 60
  }
  saveError.value = null
  editing.value = true
}

async function saveEdit(): Promise<void> {
  if (!routine.value) return
  saving.value = true
  saveError.value = null
  // Build schedule_config from helpers
  let scheduleConfig: RoutineUpdate['schedule_config'] = null
  if (form.value.schedule_type === 'cron') {
    scheduleConfig = editCronExpression.value ? { cron: editCronExpression.value } : null
  } else if (form.value.schedule_type === 'interval') {
    scheduleConfig = editIntervalSeconds.value > 0 ? { seconds: editIntervalSeconds.value } : null
  }
  try {
    routine.value = await routinesApi.update(routine.value.id, {
      ...form.value,
      schedule_config: scheduleConfig,
    })
    editing.value = false
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : 'Save failed'
  } finally {
    saving.value = false
  }
}

// ── Actions ──────────────────────────────────────────────────────────────────
async function moveAction(action: Action, direction: 'up' | 'down'): Promise<void> {
  if (!routine.value) return
  const newPos = direction === 'up' ? action.position - 1 : action.position + 1
  actionError.value = null
  try {
    await routinesApi.updateAction(action.id, { position: newPos })
    await load()
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Reorder failed'
  }
}

async function removeAction(action: Action): Promise<void> {
  actionError.value = null
  try {
    await routinesApi.deleteAction(action.id)
    if (routine.value) {
      const remaining = routine.value.actions.filter((a) => a.id !== action.id)
      routine.value = {
        ...routine.value,
        actions: remaining.map((a, i) => ({ ...a, position: i + 1 })),
      }
    }
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Delete failed'
  }
}

async function addAction(): Promise<void> {
  if (!routine.value) return
  addingAction.value = true
  actionError.value = null
  // Build config from local helpers
  const config: ActionCreate['config'] =
    actionForm.value.action_type === 'echo'
      ? { message: echoMessage.value }
      : { seconds: sleepSeconds.value }
  try {
    const created = await routinesApi.createAction(routine.value.id, {
      action_type: actionForm.value.action_type,
      config,
    })
    routine.value = { ...routine.value, actions: [...routine.value.actions, created] }
    // Reset form
    actionForm.value = { action_type: 'echo', config: { message: '' } }
    echoMessage.value = ''
    sleepSeconds.value = 5
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : 'Add failed'
  } finally {
    addingAction.value = false
  }
}

// ── Run Now ───────────────────────────────────────────────────────────────────
async function runNow(): Promise<void> {
  if (!routine.value) return
  runNowLoading.value = true
  try {
    await routinesApi.runNow(routine.value.id)
    toast.add({ severity: 'success', summary: 'Started', detail: `${routine.value.name} is running`, life: 3000 })
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'Failed to start'
    toast.add({ severity: 'error', summary: 'Run Now failed', detail: msg, life: 4000 })
  } finally {
    runNowLoading.value = false
  }
}
</script>
