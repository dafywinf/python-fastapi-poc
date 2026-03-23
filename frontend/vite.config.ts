import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass(req) {
          // /auth/callback is a SPA route — the backend redirects here with
          // ?token= after a successful OAuth exchange.  Serve the SPA shell so
          // Vue Router handles it.  All other /auth/* paths (e.g.
          // /auth/google/login, /auth/google/callback, /auth/token) must reach
          // the FastAPI backend, so return null for those.
          if (
            req.url?.startsWith('/auth/callback') &&
            req.headers.accept?.includes('text/html')
          ) {
            return '/index.html'
          }
          return null
        },
      },
      '/users': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass(req) {
          // Browser navigations to /users are served the SPA so Vue Router handles the route.
          // API fetch calls (Accept: application/json) are proxied to the backend.
          if (req.headers.accept?.includes('text/html')) {
            return '/index.html'
          }
          return null
        },
      },
      '/routines': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html'
          return null
        },
      },
      '/actions': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html'
          return null
        },
      },
      '/executions': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        bypass(req) {
          if (req.headers.accept?.includes('text/html')) return '/index.html'
          return null
        },
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
