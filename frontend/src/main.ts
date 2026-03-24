import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import router from './router'
import { primevuePt } from './primevue-pt'
import './style.css'

const app = createApp(App)
const pinia = createPinia()
const queryClient = new QueryClient()

app.use(pinia)
app.use(router)
app.use(VueQueryPlugin, { queryClient })
app.use(PrimeVue, { unstyled: true, pt: primevuePt })
app.use(ToastService)

app.mount('#app')
