/**
 * PrimeVue pass-through configuration.
 *
 * Defines Tailwind utility classes for every PrimeVue component used in the
 * app. Passed to app.use(PrimeVue, { unstyled: true, pt: primevuePt }).
 *
 * All brand colors reference semantic tokens defined in style.css @theme:
 *   bg-app-red, text-app-red, border-app-teal, etc.
 * To retheme the entire app, edit the @theme block in style.css only.
 *
 * PrimeVue PT docs: https://primevue.org/passthrough/
 */

type Cls = {
  class: string | Record<string, boolean> | (string | Record<string, boolean>)[]
}
type DynCls = (opts: { props: Record<string, unknown>; context?: Record<string, unknown> }) => Cls

export const primevuePt: Record<string, Record<string, Cls | DynCls>> = {
  // ── Button ───────────────────────────────────────────────────────────────
  button: {
    root: (({ props }) => ({
      class: [
        'inline-flex items-center gap-1.5 font-semibold cursor-pointer transition-colors rounded-sm border border-transparent uppercase tracking-wider',
        props['size'] === 'small' ? 'px-2.5 py-1 text-[12px]' : 'px-4 py-2 text-[13px]',
        !props['severity'] || props['severity'] === 'primary'
          ? 'bg-app-red text-white hover:opacity-90 border-app-red'
          : props['severity'] === 'secondary'
            ? 'bg-transparent text-app-muted border-app-border hover:bg-app-border/30'
            : props['severity'] === 'danger'
              ? 'bg-transparent text-app-red border-app-red/40 hover:bg-red-50'
              : 'bg-transparent text-app-muted border-app-border hover:bg-app-border/30',
        props['disabled'] ? 'opacity-50 cursor-not-allowed pointer-events-none' : '',
      ],
    })) as DynCls,
  },

  // ── DataTable ─────────────────────────────────────────────────────────────
  datatable: {
    root: { class: 'w-full' },
    table: { class: 'w-full border-collapse text-[13px]' },
    thead: { class: '' },
    headerRow: { class: '' },
    headerCell: {
      class: 'px-4 py-2 text-left text-[11px] font-bold text-gray-500 uppercase tracking-[0.05em] bg-app-border/20 border-b border-app-border',
    },
    tbody: { class: '' },
    row: { class: 'border-t border-app-border/60 hover:bg-app-border/30 transition-colors' },
    bodyCell: { class: 'px-4 py-2 text-app-text' },
    emptyMessage: { class: '' },
    emptyMessageCell: { class: 'px-4 py-10 text-center text-[13px] text-app-muted' },
  },

  // ── Column ────────────────────────────────────────────────────────────────
  column: {
    headerCell: {
      class: 'px-4 py-2 text-left text-[11px] font-bold text-gray-500 uppercase tracking-[0.05em] bg-app-border/20 border-b border-app-border',
    },
    bodyCell: { class: 'px-4 py-2 text-app-text' },
  },

  // ── Dialog ───────────────────────────────────────────────────────────────
  dialog: {
    root: { class: 'bg-app-card rounded-lg shadow-2xl border border-app-border w-[480px] max-w-[92vw] mx-auto' },
    mask: { class: 'fixed inset-0 bg-black/50 z-50 flex items-center justify-center' },
    header: { class: 'flex items-center justify-between px-6 pt-5 pb-0 border-b border-app-border/60' },
    title: { class: 'text-[13px] font-bold text-app-text uppercase tracking-[0.05em] pb-4' },
    headerActions: { class: 'flex items-center pb-4' },
    closeButton: { class: 'p-1 rounded hover:bg-app-border/30 text-app-muted hover:text-gray-700 transition-colors cursor-pointer border-none bg-transparent' },
    closeIcon: { class: 'w-4 h-4' },
    content: { class: 'px-6 py-5' },
    footer: { class: 'flex justify-end gap-2 px-6 pb-5 pt-2 border-t border-app-border/60' },
  },

  // ── InputText ─────────────────────────────────────────────────────────────
  inputtext: {
    root: {
      class: 'w-full px-3 py-2 border border-app-border rounded text-[13px] text-app-text outline-none transition-colors focus:border-app-red focus:ring-2 focus:ring-app-red/15 font-[inherit] bg-app-card',
    },
  },

  // ── Textarea ──────────────────────────────────────────────────────────────
  textarea: {
    root: {
      class: 'w-full px-3 py-2 border border-app-border rounded text-[13px] text-app-text outline-none transition-colors focus:border-app-red focus:ring-2 focus:ring-app-red/15 font-[inherit] resize-y bg-app-card',
    },
  },

  // ── Select ────────────────────────────────────────────────────────────────
  select: {
    root: { class: 'flex items-center border border-app-border rounded text-[13px] bg-app-card cursor-pointer transition-colors focus-within:border-app-red focus-within:ring-2 focus-within:ring-app-red/15' },
    label: { class: 'flex-1 px-3 py-1.5 text-app-text text-[13px]' },
    dropdown: { class: 'px-2 text-app-muted flex items-center' },
    overlay: { class: 'bg-app-card border border-app-border rounded shadow-lg mt-1 z-50 overflow-hidden' },
    listContainer: { class: 'overflow-y-auto max-h-60' },
    list: { class: 'py-1' },
    option: { class: 'px-3 py-2 text-[13px] text-app-text hover:bg-app-red/5 hover:text-app-red cursor-pointer' },
  },

  // ── Checkbox ──────────────────────────────────────────────────────────────
  checkbox: {
    root: { class: 'flex items-center gap-2 cursor-pointer select-none' },
    box: { class: 'w-4 h-4 border-2 border-app-border rounded transition-colors' },
    icon: { class: 'w-3 h-3 text-white' },
  },

  // ── ProgressSpinner ───────────────────────────────────────────────────────
  progressspinner: {
    root: { class: 'relative w-8 h-8' },
    circle: { class: 'animate-spin stroke-app-red' },
  },

  // ── Tag ───────────────────────────────────────────────────────────────────
  tag: {
    root: (({ props }) => ({
      class: [
        'inline-flex items-center px-1.5 py-0.5 rounded-sm text-[10px] font-bold uppercase tracking-wide border',
        !props['severity'] || props['severity'] === 'primary'
          ? 'bg-app-red/10 text-app-red border-app-red/20'
          : props['severity'] === 'secondary'
            ? 'bg-app-border/20 text-app-muted border-app-border'
            : props['severity'] === 'success'
              ? 'bg-green-100 text-green-700 border-green-200'
              : props['severity'] === 'danger'
                ? 'bg-red-100 text-app-red border-red-200'
                : props['severity'] === 'warn'
                  ? 'bg-app-amber/15 text-yellow-700 border-app-amber/30'
                  : props['severity'] === 'info'
                    ? 'bg-app-teal/15 text-teal-700 border-app-teal/30'
                    : 'bg-app-border/20 text-app-muted border-app-border',
      ],
    })) as DynCls,
    value: { class: '' },
  },

  // ── Paginator ─────────────────────────────────────────────────────────────
  paginator: {
    root: { class: 'flex items-center justify-end gap-0.5 px-3 py-1.5 border-t border-app-border bg-app-card' },
    first: { class: 'w-7 h-7 flex items-center justify-center rounded text-[11px] text-app-muted hover:bg-app-border/40 hover:text-app-text transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed' },
    prev: { class: 'w-7 h-7 flex items-center justify-center rounded text-[11px] text-app-muted hover:bg-app-border/40 hover:text-app-text transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed' },
    next: { class: 'w-7 h-7 flex items-center justify-center rounded text-[11px] text-app-muted hover:bg-app-border/40 hover:text-app-text transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed' },
    last: { class: 'w-7 h-7 flex items-center justify-center rounded text-[11px] text-app-muted hover:bg-app-border/40 hover:text-app-text transition-colors cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed' },
    pages: { class: 'flex gap-0.5 items-center' },
    page: (({ context }) => ({
      class: [
        'w-7 h-7 flex items-center justify-center rounded text-[12px] transition-colors cursor-pointer',
        context?.['active']
          ? 'bg-app-red text-white font-bold'
          : 'text-app-muted hover:bg-app-border/40 hover:text-app-text',
      ],
    })) as DynCls,
    current: { class: 'hidden' },
  },

  // ── Toast ─────────────────────────────────────────────────────────────────
  toast: {
    root: { class: 'fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none' },
    message: (({ props }) => ({
      class: [
        'flex items-start gap-3 px-4 py-3 rounded shadow-lg pointer-events-auto min-w-72 border',
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
    summary: { class: 'text-[13px] font-bold text-app-text uppercase tracking-wide' },
    detail: { class: 'text-[13px] text-app-muted' },
    closeButton: { class: 'ml-auto p-0.5 rounded hover:bg-black/5 text-app-muted hover:text-app-muted border-none bg-transparent cursor-pointer' },
    closeIcon: { class: 'w-4 h-4' },
  },
}
