import { createRouter, createWebHashHistory } from 'vue-router'
import AbsenView    from '../views/AbsenView.vue'
import RiwayatView  from '../views/RiwayatView.vue'
import AdminView    from '../views/AdminView.vue'

const routes = [
  { path: '/',          component: AbsenView,    name: 'absen' },
  { path: '/riwayat',  component: RiwayatView,  name: 'riwayat' },
  { path: '/admin',    component: AdminView,    name: 'admin' }
]

export default createRouter({ history: createWebHashHistory(), routes })
