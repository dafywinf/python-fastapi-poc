<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">Welcome</h1>
      <p class="login-subtitle">Sign in to manage sequences</p>
      <a href="/auth/google/login" class="login-button">
        Sign in with Google
      </a>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.login-card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 2.5rem 3rem;
  text-align: center;
  max-width: 380px;
  width: 100%;
}

.login-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #f8fafc;
  margin-bottom: 0.5rem;
}

.login-subtitle {
  color: #94a3b8;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.login-button {
  display: inline-block;
  background: #3b82f6;
  color: #fff;
  padding: 0.625rem 1.5rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s;
}

.login-button:hover {
  background: #2563eb;
}
</style>
