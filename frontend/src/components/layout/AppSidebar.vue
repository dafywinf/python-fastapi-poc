<template>
  <aside class="sidebar">
    <nav class="sidebar__nav">
      <RouterLink to="/sequences" class="sidebar__item" active-class="sidebar__item--active">
        <span class="sidebar__icon">&#9776;</span>
        <span>Sequences</span>
      </RouterLink>
    </nav>
    <div class="sidebar__footer">
      <span class="sidebar__version">v0.1.0</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 1rem 0;
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0 0.75rem;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.375rem;
  color: #475569;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.15s, color 0.15s;
}

.sidebar__item:hover {
  background: #e2e8f0;
  color: #1e293b;
}

.sidebar__item--active {
  background: #e0e7ff;
  color: #3730a3;
}

.sidebar__icon {
  width: 1rem;
  text-align: center;
  font-size: 1rem;
}

.sidebar__footer {
  padding: 0 1.5rem;
}

.sidebar__version {
  font-size: 0.75rem;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
}
</style>
