import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/sequences': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        bypass(req) {
          // Browser navigation (Accept: text/html) should be served the SPA
          // shell so Vue Router handles the route client-side.  API fetch calls
          // (Accept: application/json) are proxied to the backend as normal.
          if (req.headers.accept?.includes('text/html')) {
            return '/index.html'
          }
          return null
        },
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
