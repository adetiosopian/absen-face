<template>
  <div class="statistik-view">
    <div class="panel-header">
      <h1>Statistik <span class="gold">Kehadiran</span></h1>
      <p>Ringkasan &amp; analisis data absensi harian</p>
    </div>

    <!-- Stat Cards -->
    <div class="stats-grid">
      <div class="stat-card glass-card" v-for="c in cards" :key="c.lbl">
        <div class="sc-icon">{{ c.icon }}</div>
        <div class="sc-val" :style="c.color ? `color:${c.color}` : ''">{{ c.val }}</div>
        <div class="sc-lbl">{{ c.lbl }}</div>
      </div>
    </div>

    <!-- Charts row -->
    <div class="chart-row">
      <!-- Bar: 7 days -->
      <div class="chart-card glass-card">
        <div class="chart-title">📅 Kehadiran 7 Hari Terakhir</div>
        <canvas ref="barRef" class="bar-canvas"></canvas>
      </div>

      <!-- Donut: today -->
      <div class="chart-card donut-card glass-card">
        <div class="chart-title">🎯 Status Hari Ini</div>
        <canvas ref="donutRef" width="200" height="200"></canvas>
        <div class="donut-legend">
          <span class="leg-item"><span class="leg-dot" style="background:#d4a017"></span>Hadir</span>
          <span class="leg-item"><span class="leg-dot" style="background:#1b2c4e;border:1px solid #d4a017"></span>Tidak Hadir</span>
        </div>
      </div>
    </div>

    <!-- Today's attendance list -->
    <div class="today-section glass-card">
      <div class="ts-header">
        <span class="ts-title">Detail Absensi Hari Ini</span>
        <span class="ts-date">{{ todayDisplay }}</span>
      </div>
      <div v-if="loading" class="ts-loading">⏳ Memuat…</div>
      <div v-else-if="!todayRecords.length" class="ts-empty">Belum ada absensi hari ini</div>
      <div v-else class="ts-grid">
        <div v-for="st in mergedToday" :key="st.nim" class="ts-row">
          <div class="ts-av">
            <img v-if="st.photo_url" :src="st.photo_url" :alt="st.name" />
            <span v-else>{{ initials(st.name) }}</span>
          </div>
          <div class="ts-info">
            <div class="ts-name">{{ st.name }}</div>
            <div class="ts-nim">{{ st.nim }}</div>
          </div>
          <div class="ts-times">
            <span :class="['badge', st.masuk ? 'badge-masuk' : '']" class="ts-badge">
              {{ st.masuk ? '🟢 ' + st.masukTime : '—' }}
            </span>
            <span :class="['badge', st.pulang ? 'badge-pulang' : '']" class="ts-badge">
              {{ st.pulang ? '🔴 ' + st.pulangTime : '—' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import axios from 'axios'

const barRef   = ref(null)
const donutRef = ref(null)
const loading  = ref(false)

const stats        = ref({ total_students:0, hadir_today:0, pulang_today:0, tidak_hadir:0, week_data:[] })
const todayRecords = ref([])
const students     = ref([])

// ── Helpers ──────────────────────────────────────────────
const initials     = name => (name||'?').split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2)
const today        = ()   => new Date().toISOString().slice(0,10)
const todayDisplay = computed(() =>
  new Date().toLocaleDateString('id-ID', { weekday:'long', day:'numeric', month:'long', year:'numeric' })
)

// ── Computed cards ───────────────────────────────────────
const cards = computed(() => [
  { icon:'👥', val: stats.value.total_students, lbl:'Total Terdaftar' },
  { icon:'✅', val: stats.value.hadir_today,    lbl:'Hadir Hari Ini',     color:'var(--success)' },
  { icon:'🏁', val: stats.value.pulang_today,   lbl:'Sudah Pulang' },
  { icon:'❌', val: stats.value.tidak_hadir,    lbl:'Tidak Hadir',        color:'var(--danger)' },
  { icon:'📈', val: pct.value + '%',            lbl:'Persentase Hadir',   color:'var(--gold-400)' },
])
const pct = computed(() =>
  stats.value.total_students
    ? Math.round(stats.value.hadir_today / stats.value.total_students * 100)
    : 0
)

// ── Merge today records per student ──────────────────────
const mergedToday = computed(() => {
  const map = {}
  students.value.forEach(s => {
    map[s.nim] = { nim: s.nim, name: s.name, photo_url: s.photo_url, masuk: false, pulang: false, masukTime: null, pulangTime: null }
  })
  todayRecords.value.forEach(r => {
    if (!map[r.nim]) map[r.nim] = { nim: r.nim, name: r.name, photo_url: null, masuk:false, pulang:false }
    if (r.type === 'masuk')  { map[r.nim].masuk = true;  map[r.nim].masukTime  = r.time }
    if (r.type === 'pulang') { map[r.nim].pulang = true; map[r.nim].pulangTime = r.time }
  })
  return Object.values(map).filter(s => s.masuk || s.pulang)
})

// ── Load data ─────────────────────────────────────────────
const loadAll = async () => {
  loading.value = true
  try {
    const [sRes, attRes, stRes] = await Promise.all([
      axios.get('/api/stats'),
      axios.get('/api/attendance', { params: { date: today() } }),
      axios.get('/api/students')
    ])
    stats.value        = sRes.data
    todayRecords.value = attRes.data
    students.value     = stRes.data
    await nextTick()
    drawBar()
    drawDonut()
  } finally { loading.value = false }
}

// ── Bar chart ─────────────────────────────────────────────
const drawBar = () => {
  const canvas = barRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const W = canvas.offsetWidth, H = 220
  canvas.width = W; canvas.height = H
  ctx.clearRect(0, 0, W, H)

  const data = stats.value.week_data
  if (!data.length) return
  const max   = Math.max(...data.map(d => d.count), 1)
  const pL=40, pR=14, pT=18, pB=32
  const cW = W - pL - pR, cH = H - pT - pB
  const bW = Math.floor(cW / data.length * .55)
  const sp = cW / data.length

  // Grid lines
  for (let i = 0; i <= 4; i++) {
    const y = pT + cH - (i/4)*cH
    ctx.strokeStyle = 'rgba(212,160,23,.08)'; ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(pL, y); ctx.lineTo(W-pR, y); ctx.stroke()
    ctx.fillStyle = 'rgba(160,144,128,.55)'; ctx.font = '10px Outfit'
    ctx.fillText(Math.round(max*i/4), 2, y+4)
  }

  data.forEach((d, i) => {
    const x   = pL + i*sp + (sp-bW)/2
    const bH  = Math.max(2, (d.count/max)*cH)
    const y   = pT + cH - bH
    const grad = ctx.createLinearGradient(x, y, x, pT+cH)
    grad.addColorStop(0, '#f5c842'); grad.addColorStop(1, '#b8860b')
    ctx.fillStyle = grad
    ctx.shadowColor = 'rgba(212,160,23,.45)'; ctx.shadowBlur = 10
    ctx.beginPath(); ctx.roundRect(x, y, bW, bH, [4,4,0,0]); ctx.fill()
    ctx.shadowBlur = 0
    ctx.fillStyle = 'rgba(160,144,128,.7)'; ctx.font = '10px Outfit'
    ctx.textAlign = 'center'
    ctx.fillText(d.label, x+bW/2, H-8)
    if (d.count > 0) {
      ctx.fillStyle = '#f5c842'
      ctx.fillText(d.count, x+bW/2, y-4)
    }
  })
  ctx.textAlign = 'left'
}

// ── Donut chart ───────────────────────────────────────────
const drawDonut = () => {
  const canvas = donutRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const W = canvas.width, H = canvas.height
  ctx.clearRect(0, 0, W, H)
  const cx = W/2, cy = H/2, r = Math.min(W,H)/2 - 16
  const hadir  = stats.value.hadir_today
  const tidak  = stats.value.tidak_hadir
  const total  = hadir + tidak || 1
  const slices = [
    { val: hadir, color: '#d4a017' },
    { val: tidak, color: '#1b2c4e' }
  ]
  let angle = -Math.PI/2
  slices.forEach(s => {
    const sweep = (s.val/total)*Math.PI*2
    ctx.beginPath(); ctx.moveTo(cx,cy)
    ctx.arc(cx, cy, r, angle, angle+sweep)
    ctx.closePath(); ctx.fillStyle = s.color
    ctx.shadowColor = s.color; ctx.shadowBlur = 8
    ctx.fill(); ctx.shadowBlur = 0
    angle += sweep
  })
  // hole
  ctx.beginPath(); ctx.arc(cx, cy, r*.55, 0, Math.PI*2)
  ctx.fillStyle = '#0d1628'; ctx.fill()
  // center text
  ctx.textAlign = 'center'; ctx.fillStyle = '#f5c842'
  ctx.font = `bold 22px Rajdhani, sans-serif`
  ctx.fillText(`${Math.round(hadir/total*100)}%`, cx, cy+4)
  ctx.fillStyle = 'rgba(160,144,128,.7)'; ctx.font = '10px Outfit'
  ctx.fillText('Hadir', cx, cy+18)
  ctx.textAlign = 'left'
}

onMounted(loadAll)
</script>

<style scoped>
.statistik-view { display: flex; flex-direction: column; gap: 1.4rem; }

/* Stat cards */
.stats-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: .9rem; }
.stat-card {
  display: flex; flex-direction: column; align-items: center; gap: .35rem;
  padding: 1.3rem .8rem; text-align: center; transition: var(--trans);
}
.stat-card:hover { border-color: var(--gold-400); box-shadow: 0 0 22px var(--gold-glow); }
.sc-icon { font-size: 1.8rem; }
.sc-val  { font-family: 'Rajdhani', sans-serif; font-size: 2rem; font-weight: 700; color: var(--gold-400); text-shadow: 0 0 14px var(--gold-glow); }
.sc-lbl  { font-size: .7rem; color: var(--text-secondary); }

/* Charts row */
.chart-row { display: grid; grid-template-columns: 1fr 260px; gap: 1.2rem; }
.chart-card { padding: 1.3rem; display: flex; flex-direction: column; gap: .9rem; }
.chart-title { font-weight: 700; font-size: .88rem; color: var(--gold-400); letter-spacing: .04em; }
.bar-canvas  { width: 100%; }

.donut-card { align-items: center; }
.donut-legend { display: flex; gap: 1rem; font-size: .78rem; }
.leg-item { display: flex; align-items: center; gap: .35rem; }
.leg-dot  { width: 12px; height: 12px; border-radius: 3px; flex-shrink: 0; }

/* Today section */
.today-section { padding: 1.3rem; display: flex; flex-direction: column; gap: 1rem; }
.ts-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .5rem; }
.ts-title  { font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; font-weight: 700; }
.ts-date   { font-size: .78rem; color: var(--text-secondary); }
.ts-loading, .ts-empty { text-align: center; color: var(--text-muted); padding: 1.5rem; font-size: .85rem; }

.ts-grid { display: flex; flex-direction: column; gap: .5rem; max-height: 360px; overflow-y: auto; }
.ts-row {
  display: flex; align-items: center; gap: .9rem; padding: .6rem .5rem;
  border-bottom: 1px solid rgba(212,160,23,.05);
}
.ts-row:last-child { border-bottom: none; }
.ts-av {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  background: var(--sky-500); border: 1px solid var(--glass-border);
  display: flex; align-items: center; justify-content: center;
  font-size: .82rem; font-weight: 700; color: var(--gold-400); overflow: hidden;
}
.ts-av img { width: 100%; height: 100%; object-fit: cover; }
.ts-info { flex: 1; min-width: 0; }
.ts-name { font-weight: 700; font-size: .85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ts-nim  { font-size: .72rem; color: var(--gold-400); }
.ts-times { display: flex; gap: .4rem; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }
.ts-badge { font-size: .72rem !important; padding: .2rem .5rem !important; }

@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(3,1fr); }
  .chart-row  { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .stats-grid { grid-template-columns: repeat(2,1fr); }
}
</style>
