<template>
  <aside
    class="w-[220px] shrink-0 bg-slate-50 border-r border-slate-200 flex flex-col justify-between py-4 hidden md:flex"
  >
    <nav aria-label="Sidebar" class="flex flex-col gap-1 px-3">
      <RouterLink
        to="/routines"
        class="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition-colors no-underline"
        active-class="bg-indigo-100 text-indigo-800"
      >
        <span class="w-4 text-center">&#9776;</span>
        <span>Routines</span>
      </RouterLink>
      <RouterLink
        to="/history"
        class="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition-colors no-underline"
        active-class="bg-indigo-100 text-indigo-800"
      >
        <span class="w-4 text-center">&#128336;</span>
        <span>History</span>
      </RouterLink>
    </nav>
    <div class="px-6">
      <span class="text-xs text-slate-500">v0.1.0</span>
    </div>
  </aside>
</template>
