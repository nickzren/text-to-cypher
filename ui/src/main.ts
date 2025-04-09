// src/main.ts
import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'
import 'primeicons/primeicons.css'
import './main.css';

const app = createApp(App)

app.use(PrimeVue, {
  theme: { preset: Aura }
})

app.use(ToastService)
app.directive('tooltip', Tooltip)
app.mount('#app')