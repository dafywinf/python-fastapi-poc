/**
 * PrimeVue pass-through configuration.
 *
 * Defines Tailwind utility classes for every PrimeVue component used in the
 * app.  Passed to app.use(PrimeVue, { unstyled: true, pt: primevuePt }).
 *
 * PrimeVue PT docs: https://primevue.org/passthrough/
 * Each component's PT slots are listed in its own API docs page.
 */

type Cls = { class: string | Record<string, boolean> | (string | Record<string, boolean>)[] }
type DynCls = (opts: { props: Record<string, unknown> }) => Cls

export const primevuePt: Record<string, Record<string, Cls | DynCls>> = {
  // ── Button ───────────────────────────────────────────────────────────────
  button: {
    root: (({ props }) => ({
      class: [
        'inline-flex items-center gap-1.5 font-medium cursor-pointer transition-colors rounded-md border border-transparent',
        // Size
        props['size'] === 'small'
          ? 'px-2.5 py-1 text-xs'
          : 'px-4 py-2 text-sm',
        // Severity
        !props['severity'] || props['severity'] === 'primary'
          ? 'bg-indigo-600 text-white hover:bg-indigo-700'
          : props['severity'] === 'secondary'
          ? 'bg-transparent text-slate-600 border-slate-300 hover:bg-slate-50'
          : props['severity'] === 'danger'
          ? 'bg-transparent text-red-600 border-red-300 hover:bg-red-50'
          : 'bg-transparent text-slate-600 border-slate-300 hover:bg-slate-50',
        // Disabled
        props['disabled'] ? 'opacity-60 cursor-not-allowed pointer-events-none' : '',
      ],
    })) as DynCls,
  },

  // ── DataTable ─────────────────────────────────────────────────────────────
  datatable: {
    root: { class: 'w-full' },
    table: { class: 'w-full border-collapse text-sm' },
    thead: { class: '' },
    headerRow: { class: '' },
    headerCell: { class: 'px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide bg-slate-50 border-b border-slate-200' },
    tbody: { class: '' },
    row: { class: 'border-t border-slate-100 hover:bg-slate-50 transition-colors' },
    bodyCell: { class: 'px-4 py-3 text-slate-900' },
    emptyMessage: { class: '' },
    emptyMessageCell: { class: 'px-4 py-10 text-center text-sm text-slate-400' },
  },

  // ── Column (used inside DataTable) ───────────────────────────────────────
  column: {
    headerCell: { class: 'px-4 py-2.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide bg-slate-50 border-b border-slate-200' },
    bodyCell: { class: 'px-4 py-3 text-slate-900' },
  },

  // ── Dialog ───────────────────────────────────────────────────────────────
  dialog: {
    root: { class: 'bg-white rounded-xl shadow-2xl w-[480px] max-w-[92vw] mx-auto' },
    mask: { class: 'fixed inset-0 bg-slate-900/45 z-50 flex items-center justify-center' },
    header: { class: 'flex items-center justify-between px-6 pt-6 pb-0' },
    title: { class: 'text-lg font-semibold text-slate-900' },
    headerActions: { class: 'flex items-center' },
    closeButton: { class: 'p-1.5 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer border-none bg-transparent' },
    closeIcon: { class: 'w-4 h-4' },
    content: { class: 'px-6 py-5' },
    footer: { class: 'flex justify-end gap-3 px-6 pb-6 pt-2' },
  },

  // ── InputText ─────────────────────────────────────────────────────────────
  inputtext: {
    root: { class: 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 outline-none transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 font-[inherit] bg-white' },
  },

  // ── Textarea ──────────────────────────────────────────────────────────────
  textarea: {
    root: { class: 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm text-slate-900 outline-none transition-colors focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 font-[inherit] resize-y bg-white' },
  },

  // ── Select (formerly Dropdown) ────────────────────────────────────────────
  select: {
    root: { class: 'flex items-center border border-slate-300 rounded-md text-sm bg-white cursor-pointer transition-colors focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20' },
    label: { class: 'flex-1 px-3 py-2 text-slate-900 text-sm' },
    dropdown: { class: 'px-2 text-slate-400 flex items-center' },
    panel: { class: 'bg-white border border-slate-200 rounded-md shadow-lg mt-1 z-50 overflow-hidden' },
    listContainer: { class: 'overflow-y-auto max-h-60' },
    list: { class: 'py-1' },
    option: { class: 'px-3 py-2 text-sm text-slate-900 hover:bg-indigo-50 cursor-pointer' },
  },

  // ── Checkbox ──────────────────────────────────────────────────────────────
  checkbox: {
    root: { class: 'flex items-center gap-2 cursor-pointer select-none' },
    box: { class: 'w-4 h-4 border-2 border-slate-300 rounded transition-colors' },
    icon: { class: 'w-3 h-3 text-white' },
  },

  // ── ProgressSpinner ───────────────────────────────────────────────────────
  progressspinner: {
    root: { class: 'relative w-8 h-8' },
    circle: { class: 'animate-spin stroke-indigo-600' },
  },

  // ── Tag ───────────────────────────────────────────────────────────────────
  tag: {
    root: (({ props }) => ({
      class: [
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
        !props['severity'] || props['severity'] === 'primary'
          ? 'bg-indigo-100 text-indigo-700'
          : props['severity'] === 'secondary'
          ? 'bg-slate-100 text-slate-600'
          : props['severity'] === 'success'
          ? 'bg-green-100 text-green-700'
          : props['severity'] === 'danger'
          ? 'bg-red-100 text-red-600'
          : props['severity'] === 'warn'
          ? 'bg-yellow-100 text-yellow-700'
          : props['severity'] === 'info'
          ? 'bg-blue-100 text-blue-700'
          : 'bg-slate-100 text-slate-600',
      ],
    })) as DynCls,
    value: { class: '' },
  },

  // ── Toast ─────────────────────────────────────────────────────────────────
  toast: {
    root: { class: 'fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none' },
    message: (({ props }) => ({
      class: [
        'flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg pointer-events-auto min-w-72 border',
        props['message'] && (props['message'] as Record<string, string>)['severity'] === 'success'
          ? 'bg-green-50 border-green-200'
          : props['message'] && (props['message'] as Record<string, string>)['severity'] === 'error'
          ? 'bg-red-50 border-red-200'
          : props['message'] && (props['message'] as Record<string, string>)['severity'] === 'warn'
          ? 'bg-yellow-50 border-yellow-200'
          : 'bg-blue-50 border-blue-200',
      ],
    })) as DynCls,
    messageContent: { class: 'flex flex-col gap-0.5 flex-1' },
    summary: { class: 'text-sm font-semibold text-slate-900' },
    detail: { class: 'text-sm text-slate-600' },
    closeButton: { class: 'ml-auto p-0.5 rounded hover:bg-black/5 text-slate-400 hover:text-slate-600 border-none bg-transparent cursor-pointer' },
    closeIcon: { class: 'w-4 h-4' },
  },
}
