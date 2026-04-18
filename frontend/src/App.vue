<template>
  <!-- Stars background -->
  <canvas id="stars-canvas"></canvas>

  <!-- Top Navigation -->
  <header class="topnav">
    <div class="brand">
      <span class="brand-icon">◈</span>
      <span class="brand-name">Face<span class="gold">Recognition</span></span>
    </div>
    <div class="clock-area">
      <div class="clock-time">{{ clock }}</div>
      <div class="clock-date">{{ dateStr }}</div>
    </div>
  </header>

  <!-- App Shell -->
  <div class="app-shell">
    <!-- Sidebar (Desktop) -->
    <nav class="sidebar">
      <router-link to="/" class="nav-item" active-class="nav-active">
        <span class="nav-ico">🤳</span><span class="nav-lbl">Absen Wajah</span>
      </router-link>
      <router-link to="/riwayat" class="nav-item" active-class="nav-active">
        <span class="nav-ico">📋</span><span class="nav-lbl">Riwayat</span>
      </router-link>
      <router-link to="/admin" class="nav-item" active-class="nav-active">
        <span class="nav-ico">⚙️</span><span class="nav-lbl">Admin Panel</span>
      </router-link>
    </nav>

    <!-- Mobile Nav (Bottom) -->
    <nav class="mobile-nav">
      <router-link to="/" class="nav-item" active-class="nav-active">
        <span class="nav-ico">🤳</span><span class="nav-lbl">Absen</span>
      </router-link>
      <router-link to="/riwayat" class="nav-item" active-class="nav-active">
        <span class="nav-ico">📋</span><span class="nav-lbl">Riwayat</span>
      </router-link>
      <router-link to="/admin" class="nav-item" active-class="nav-active">
        <span class="nav-ico">⚙️</span><span class="nav-lbl">Admin</span>
      </router-link>
    </nav>

    <!-- Content -->
    <main class="content">
      <router-view v-slot="{ Component }">
        <Transition name="fade" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>
  </div>

  <!-- Global Toast Container -->
  <Teleport to="body">
    <div class="toast-wrap">
      <div
        v-for="t in toasts" :key="t.id"
        :class="['toast', t.type]"
      >{{ t.msg }}</div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted, provide } from 'vue'

// ── Clock ────────────────────────────────────────────────
const clock   = ref('')
const dateStr = ref('')
let   clockTimer

const DAYS   = ['Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu']
const MONTHS = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des']
const pad = n => String(n).padStart(2,'0')

const tickClock = () => {
  const d = new Date()
  clock.value   = `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  dateStr.value = `${DAYS[d.getDay()]}, ${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`
}
tickClock()

// ── Toast system ─────────────────────────────────────────
const toasts = ref([])
const showToast = (msg, type = '', duration = 3000) => {
  const id = Date.now() + Math.random()
  toasts.value.push({ id, msg, type })
  setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id) }, duration)
}
provide('toast', showToast)

// ── Stars canvas ─────────────────────────────────────────
const initStars = () => {
  const canvas = document.getElementById('stars-canvas')
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  let W, H, stars = []

  const resize = () => {
    W = canvas.width  = window.innerWidth
    H = canvas.height = window.innerHeight
    stars = Array.from({ length: 200 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      r: Math.random() * 1.5 + .2,
      o: Math.random() * .65 + .08,
      s: Math.random() * .3 + .04,
      d: Math.random() > .5 ? 1 : -1
    }))
  }
  const draw = () => {
    ctx.clearRect(0, 0, W, H)
    stars.forEach(s => {
      s.o += s.s * .007 * s.d
      if (s.o >= .75 || s.o <= .06) s.d *= -1
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(212,160,23,${s.o.toFixed(2)})`
      ctx.fill()
    })
    requestAnimationFrame(draw)
  }
  resize()
  window.addEventListener('resize', resize)
  draw()
}

onMounted(() => {
  tickClock()
  clockTimer = setInterval(tickClock, 1000)
  initStars()
})
onUnmounted(() => clearInterval(clockTimer))
</script>

<style scoped>
/* ── Top Nav ─────────────────────────────── */
.topnav {
  position: fixed; top: 0; left: 0; right: 0; height: 62px;
  background: rgba(5,10,20,.9);
  backdrop-filter: blur(28px);
  border-bottom: 1px solid rgba(212,160,23,.18);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 1.8rem; z-index: 1000;
}

/* ── Shell ───────────────────────────────── */
.app-shell {
  display: flex;
  min-height: 100vh; padding-top: 62px;
  position: relative; z-index: 1;
}

/* ── Side Nav (Desktop) ─────────────────── */
.sidebar {
  position: fixed; top: 62px; left: 0; bottom: 0; width: 240px;
  background: rgba(5,10,20,.8);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(212,160,23,.12);
  display: flex; flex-direction: column;
  padding: 1.5rem 1rem; gap: .5rem; z-index: 900;
  transition: transform .3s ease;
}

.nav-item {
  display: flex; align-items: center; gap: .8rem;
  padding: .85rem 1.2rem;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  color: var(--text-secondary); text-decoration: none;
  font-size: .92rem; font-weight: 500;
  transition: var(--trans); cursor: pointer;
}
.nav-item:hover { background: var(--gold-faint); color: var(--gold-400); }
.nav-active {
  background: linear-gradient(135deg,rgba(212,160,23,.18),rgba(212,160,23,.05)) !important;
  border-color: var(--gold-500) !important;
  color: var(--gold-400) !important;
  box-shadow: 0 4px 15px var(--gold-glow);
}
.nav-ico { font-size: 1.4rem; }

/* ── Content ─────────────────────────────── */
.content {
  flex: 1;
  margin-left: 240px;
  padding: 2rem 2.5rem;
  min-height: calc(100vh - 62px);
  transition: margin .3s ease, padding .3s ease;
}

/* ── Mobile Navbar (Bottom) ──────────────── */
.mobile-nav {
  position: fixed; bottom: 0; left: 0; right: 0;
  height: 68px; background: rgba(5,10,20,.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(212,160,23,.2);
  display: none; align-items: center; justify-content: space-around;
  padding: 0 .5rem; z-index: 1000;
  border-radius: 20px 20px 0 0;
}
.mobile-nav .nav-item {
  flex-direction: column; gap: .2rem; padding: .4rem;
  width: auto; font-size: .65rem; border: none;
}
.mobile-nav .nav-item .nav-ico { font-size: 1.5rem; }

@media (max-width: 1024px) {
  .sidebar { width: 84px; padding: 1.2rem .5rem; }
  .sidebar .nav-lbl { display: none; }
  .content { margin-left: 84px; padding: 1.5rem; }
}

@media (max-width: 768px) {
  .sidebar { display: none; }
  .mobile-nav { display: flex; }
  .content { margin-left: 0; padding: 1rem; padding-bottom: 85px; }
  .topnav { padding: 0 1rem; }
  .clock-area { display: none; }
}

</style>
