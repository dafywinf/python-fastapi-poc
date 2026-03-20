<script setup lang="ts">
import { useAuth } from '../../composables/useAuth'

const { isAuthenticated, user, login, logout } = useAuth()
</script>

<template>
  <header class="navbar">
    <div class="navbar__brand">
      <RouterLink to="/sequences" class="navbar__logo">
        Sequence Manager
      </RouterLink>
    </div>
    <nav class="navbar__links">
      <RouterLink to="/sequences" class="navbar__link">Sequences</RouterLink>
      <RouterLink to="/users" class="navbar__link">Users</RouterLink>
    </nav>
    <div class="navbar__auth">
      <template v-if="isAuthenticated && user">
        <span class="navbar__user-email">{{ user.email }}</span>
        <button class="navbar__logout-btn" @click="logout">Logout</button>
      </template>
      <button v-else class="navbar__login-btn" @click="login">
        Sign in with Google
      </button>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.5rem;
  height: 56px;
  background: #1e293b;
  color: #f8fafc;
  border-bottom: 1px solid #334155;
  flex-shrink: 0;
}

.navbar__logo {
  font-size: 1.125rem;
  font-weight: 600;
  color: #f8fafc;
  text-decoration: none;
  letter-spacing: -0.01em;
}

.navbar__links {
  display: flex;
  gap: 1rem;
}

.navbar__link {
  color: #94a3b8;
  text-decoration: none;
  font-size: 0.875rem;
  transition: color 0.15s;
}

.navbar__link:hover,
.navbar__link.router-link-active {
  color: #f8fafc;
}

.navbar__auth {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.navbar__user-email {
  font-size: 0.8125rem;
  color: #cbd5e1;
}

.navbar__login-btn,
.navbar__logout-btn {
  background: #3b82f6;
  color: #fff;
  border: none;
  border-radius: 5px;
  padding: 0.375rem 0.875rem;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: background 0.15s;
}

.navbar__logout-btn {
  background: #475569;
}

.navbar__login-btn:hover {
  background: #2563eb;
}

.navbar__logout-btn:hover {
  background: #334155;
}
</style>
