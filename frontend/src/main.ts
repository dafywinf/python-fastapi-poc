import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import router from './router'
import { primevuePt } from './primevue-pt'
import './style.css'

// Apply saved theme before first render to avoid flash
document.documentElement.setAttribute(
  'data-theme',
  localStorage.getItem('theme') ?? 'light',
)

const app = createApp(App)
const pinia = createPinia()
const queryClient = new QueryClient()

app.use(pinia)
app.use(router)
app.use(VueQueryPlugin, { queryClient })
app.use(PrimeVue, { unstyled: true, pt: primevuePt })
app.use(ToastService)

// Last-resort handler: log unhandled errors that escape component catch blocks.
// Individual call sites are responsible for user-visible feedback (toast).
app.config.errorHandler = (err, _instance, info) => {
  console.error(`[app] Unhandled error (${info}):`, err)
}

app.mount('#app')
