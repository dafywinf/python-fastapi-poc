import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import App from './App.vue'
import router from './router'
import { primevuePt } from './primevue-pt'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, { unstyled: true, pt: primevuePt })
app.use(ToastService)

app.mount('#app')
