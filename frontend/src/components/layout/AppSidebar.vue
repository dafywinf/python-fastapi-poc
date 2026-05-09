<template>
  <aside
    class="w-64 shrink-0 bg-app-dark border-r border-white/8 flex flex-col justify-between hidden md:flex"
  >
    <div>
      <nav aria-label="Sidebar" class="py-2">
        <RouterLink
          to="/"
          class="flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium text-white/70 hover:bg-white/5 hover:text-white transition-all no-underline"
          exact-active-class="!bg-white/8 !text-white !border-l-2 !border-l-app-red !pl-[14px]"
        >
          <span class="material-symbols-outlined text-white/60 text-lg">dashboard</span>
          <span>Dashboard</span>
        </RouterLink>

        <RouterLink
          to="/routines"
          class="flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium text-white/70 hover:bg-white/5 hover:text-white transition-all no-underline"
          active-class="!bg-white/8 !text-white !border-l-2 !border-l-app-red !pl-[14px]"
        >
          <span class="material-symbols-outlined text-white/60 text-lg">list_alt</span>
          <span>Routines</span>
        </RouterLink>

        <RouterLink
          to="/history"
          class="flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium text-white/70 hover:bg-white/5 hover:text-white transition-all no-underline"
          active-class="!bg-white/8 !text-white !border-l-2 !border-l-app-red !pl-[14px]"
        >
          <span class="material-symbols-outlined text-white/60 text-lg">history</span>
          <span>History</span>
        </RouterLink>

        <RouterLink
          to="/users"
          class="flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium text-white/70 hover:bg-white/5 hover:text-white transition-all no-underline"
          active-class="!bg-white/8 !text-white !border-l-2 !border-l-app-red !pl-[14px]"
        >
          <span class="material-symbols-outlined text-white/60 text-lg">badge</span>
          <span>Users</span>
        </RouterLink>
      </nav>
    </div>

    <div class="border-t border-white/8 py-3 px-5">
      <span class="text-[10px] font-light text-white/30 uppercase tracking-[0.15em]">v0.1.0</span>
    </div>
  </aside>
</template>
