<script setup lang="ts">
import { useAuth } from '../../composables/useAuth'
import { useDarkMode } from '../../composables/useDarkMode'

const { isAuthenticated, user, login, logout } = useAuth()
const { dark, toggle } = useDarkMode()
</script>

<template>
  <header
    class="flex items-center justify-between px-6 h-12 bg-app-dark text-gray-400 flex-shrink-0 border-b border-white/8 z-50"
  >
    <div class="flex items-center gap-2">
      <div class="w-7 h-7 bg-app-red flex items-center justify-center rounded-sm shrink-0">
        <span class="material-symbols-outlined text-white text-sm">bolt</span>
      </div>
      <RouterLink to="/" class="no-underline leading-tight">
        <div class="text-[11px] font-light text-white/70 tracking-[0.18em] uppercase">Operations</div>
        <div class="text-[18px] font-bold text-white tracking-tight leading-none">Control</div>
      </RouterLink>
      <div class="ml-1 h-9 w-1 bg-app-red rounded-full opacity-80"></div>
    </div>

    <div class="flex items-center gap-3">
      <!-- Dark mode toggle -->
      <button
        :title="dark ? 'Switch to light mode' : 'Switch to dark mode'"
        class="flex items-center justify-center w-7 h-7 rounded-sm text-white/70 hover:text-white hover:bg-white/8 transition-colors"
        @click="toggle"
      >
        <span class="material-symbols-outlined text-base">
          {{ dark ? 'light_mode' : 'dark_mode' }}
        </span>
      </button>

      <template v-if="isAuthenticated && user">
        <span class="text-[12px] font-normal text-white/80" data-testid="user-email">
          {{ user.email }}
        </span>
        <button
          class="px-3 h-7 text-[12px] font-semibold uppercase tracking-wide text-white border border-white/40 rounded-sm hover:bg-white/10 transition-colors"
          @click="logout"
        >
          Sign Out
        </button>
      </template>
      <button
        v-else
        class="px-3 h-7 text-[12px] font-semibold uppercase tracking-widest text-white bg-app-red rounded-sm hover:opacity-90 transition-opacity"
        @click="login"
      >
        Sign in with Google
      </button>
    </div>
  </header>
</template>
