<template>
  <header class="navbar">
    <div class="navbar__brand">
      <RouterLink to="/sequences" class="navbar__logo">
        Sequence Manager
      </RouterLink>
    </div>
    <nav class="navbar__links">
      <RouterLink to="/sequences" class="navbar__link">Sequences</RouterLink>
    </nav>
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
</style>
