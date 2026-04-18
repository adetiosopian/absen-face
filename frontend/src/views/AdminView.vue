<template>
  <div class="admin-view">
    <div class="panel-header">
      <h1>Admin <span class="gold">Control Panel</span></h1>
      <p>Manajemen statistik, pendaftaran wajah, dan rekap kehadiran harian.</p>
    </div>

    <!-- ── Section 1: Statistik ────────────────────── -->
    <div class="admin-stats-grid">
      <div class="stat-card glass-card">
        <div class="sc-icon">✅</div>
        <div class="sc-val">{{ stats.hadir }}</div>
        <div class="sc-lbl">Hadir Hari Ini</div>
      </div>
      <div class="stat-card glass-card">
        <div class="sc-icon">📝</div>
        <div class="sc-val" style="color: var(--warning)">{{ stats.ijin }}</div>
        <div class="sc-lbl">Ijin / Sakit</div>
      </div>
      <div class="stat-card glass-card">
        <div class="sc-icon">❌</div>
        <div class="sc-val" style="color: var(--danger)">{{ stats.alfa }}</div>
        <div class="sc-lbl">Tanpa Keterangan</div>
      </div>
      <div class="stat-card glass-card">
        <div class="sc-icon">📈</div>
        <div class="sc-val" style="color: var(--gold-400)">{{ stats.percentage }}%</div>
        <div class="sc-lbl">Persentase Hadir</div>
      </div>
    </div>

    <div class="admin-main-grid">
      <!-- ── Section 2: Pendaftaran Wajah (MULTI SHOT) ─ -->
      <div class="admin-col">
        <div class="glass-card admin-section">
          <div class="section-title">✦ Pendaftaran Wajah Baru (3 Sampel)</div>
          <p class="section-desc">Posisikan wajah: 1. Depan, 2. Kiri, 3. Kanan.</p>
          
          <div class="reg-container">
            <div class="reg-camera-box">
              <video ref="videoRef" autoplay muted playsinline class="reg-video"></video>
              <canvas ref="overlayRef" class="reg-overlay"></canvas>
              <div class="cam-badge" v-if="camActive">
                <span class="dot" :class="{ 'active': faceDetected }"></span>
                {{ faceDetected ? 'Wajah Terdeteksi' : 'Mencari Wajah...' }}
              </div>
            </div>
            
            <!-- Progress Steps -->
            <div class="reg-steps">
               <div v-for="i in 3" :key="i" :class="['step-item', samples.length >= i ? 'done' : '']">
                  <div class="step-num">{{ i }}</div>
                  <div class="step-lbl">{{ i===1 ? 'Depan' : i===2 ? 'Kiri' : 'Kanan' }}</div>
               </div>
            </div>

            <div class="reg-form">
              <div class="form-group">
                <label>Nama Mahasiswa</label>
                <input v-model="form.name" type="text" placeholder="Nama Lengkap" class="field-input">
              </div>
              <div class="form-group">
                <label>NIM</label>
                <input v-model="form.nim" type="text" placeholder="Contoh: 2023001" class="field-input">
              </div>
              
              <div class="btn-group-column">
                <button class="btn-outline full-w" @click="captureSample" :disabled="samples.length >= 3 || !faceDetected">
                   📸 Ambil Sampel {{ samples.length + 1 }}/3
                </button>
                <button class="btn-gold full-w" @click="registerFace" :disabled="saving || samples.length < 3 || !form.name || !form.nim">
                  {{ saving ? 'Menyimpan...' : '✔️ SELESAI & DAFTAR' }}
                </button>
                <button class="btn-danger full-w" @click="samples = []" v-if="samples.length > 0 && !saving">
                  Reset Sampel
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Section 3: Manajemen Kehadiran Manual ────── -->
      <div class="admin-col">
        <div class="glass-card admin-section">
          <div class="section-title">📋 Manajemen Kehadiran ({{ todayStr }})</div>
          <div class="search-box">
            <input v-model="search" type="text" placeholder="Cari Nama / NIM..." class="field-input">
          </div>
          
          <div class="manual-table-wrap">
            <table class="manual-table">
              <thead>
                <tr>
                  <th>Mahasiswa</th>
                  <th>Status Hari Ini</th>
                  <th>Aksi Cepat</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="s in filteredStudents" :key="s.nim">
                  <td>
                    <div class="s-info">
                      <div class="s-name">{{ s.name }}</div>
                      <div class="s-nim">{{ s.nim }}</div>
                    </div>
                  </td>
                  <td>
                    <span :class="['badge', getStatusBadge(s.nim)]">
                      {{ getStatusText(s.nim) }}
                    </span>
                  </td>
                  <td>
                    <div class="btn-group">
                      <button class="mini-btn ijin" @click="markStatus(s, 'ijin')" :disabled="isMarked(s.nim)">Ijin</button>
                      <button class="mini-btn alfa" @click="markStatus(s, 'alfa')" :disabled="isMarked(s.nim)">Alfa</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, inject, onUnmounted } from 'vue'
import axios from 'axios'
import * as faceapi from '@vladmandic/face-api'

const toast = inject('toast')
const MODELS_URL = '/models_fix'

// Data State
const stats = ref({ total: 0, hadir: 0, ijin: 0, alfa: 0, percentage: 0 })
const students = ref([])
const attendance = ref([])
const search = ref('')
const todayStr = new Date().toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })

// Registration State
const videoRef = ref(null)
const overlayRef = ref(null)
const camActive = ref(false)
const faceDetected = ref(false)
const saving = ref(false)
const form = ref({ name: '', nim: '' })
const samples = ref([]) // <--- Variabel yang wajib ada

let stream = null
let detectTimer = null

const fetchAdminData = async () => {
  try {
    const [statRes, attRes, stRes] = await Promise.all([
      axios.get('/api/admin/stats'),
      axios.get('/api/attendance'),
      axios.get('/api/students')
    ])
    stats.value = statRes.data
    attendance.value = attRes.data
    students.value = stRes.data
  } catch (e) {
    console.error("Gagal memuat data admin:", e)
  }
}

const filteredStudents = computed(() => {
  const q = search.value.toLowerCase()
  return students.value.filter(s => s.name.toLowerCase().includes(q) || s.nim.includes(q))
})

const getStatusBadge = (nim) => {
  const rec = attendance.value.find(a => a.nim === nim)
  if (!rec) return 'badge-asing'
  if (rec.status === 'hadir') return 'badge-masuk'
  if (rec.status === 'ijin') return 'badge-pulang'
  return 'badge-asing'
}

const getStatusText = (nim) => {
  const rec = attendance.value.find(a => a.nim === nim)
  if (!rec) return 'Belum Absen'
  return rec.status.toUpperCase()
}

const isMarked = (nim) => attendance.value.some(a => a.nim === nim)

const markStatus = async (student, status) => {
  try {
    await axios.post('/api/attendance', {
      nim: student.nim,
      name: student.name,
      status: status
    })
    toast(`Berhasil: ${student.name} ditandai ${status}`, 'success')
    fetchAdminData()
  } catch (e) {
    toast(e.response?.data?.error || 'Gagal', 'error')
  }
}

// ── Camera & Recognition ──────────────────────────────────
const startCamera = async () => {
  try {
    await faceapi.nets.ssdMobilenetv1.loadFromUri(MODELS_URL)
    await faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_URL)
    await faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL)
    
    stream = await navigator.mediaDevices.getUserMedia({ video: true })
    if (videoRef.value) {
      videoRef.value.srcObject = stream
      camActive.value = true
    }
    
    detectTimer = setInterval(async () => {
      if (!videoRef.value || videoRef.value.readyState < 2) return
      const detections = await faceapi.detectSingleFace(videoRef.value, new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 }))
      faceDetected.value = !!detections
    }, 500)
  } catch (e) {
    console.error("Camera Init Error:", e)
    toast('Kamera atau Model AI gagal dimuat', 'error')
  }
}

const captureSample = async () => {
  if (!faceDetected.value) return
  try {
    const det = await faceapi.detectSingleFace(videoRef.value, new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 })).withFaceLandmarks().withFaceDescriptor()
    if (!det) return toast('Posisikan wajah lebih jelas', 'error')

    const canvas = document.createElement('canvas')
    canvas.width = 150; canvas.height = 150
    const ctx = canvas.getContext('2d')
    ctx.drawImage(videoRef.value, 0, 0, 150, 150)

    samples.value.push({
      descriptor: Array.from(det.descriptor),
      photo: canvas.toDataURL('image/jpeg')
    })
    toast(`Sampel ${samples.value.length}/3 diambil`, 'success')
  } catch (e) {
    toast('Gagal mengambil sampel', 'error')
  }
}

const registerFace = async () => {
  if (!form.value.name || !form.value.nim) return toast('Lengkapi Nama & NIM', 'error')
  saving.value = true
  try {
    await axios.post('/api/students', {
      name: form.value.name,
      nim: form.value.nim,
      descriptors: samples.value.map(s => s.descriptor),
      photos: samples.value.map(s => s.photo)
    })
    toast('Pendaftaran Berhasil!', 'success')
    form.value = { name: '', nim: '' }
    samples.value = []
    fetchAdminData()
  } catch (e) {
    toast(e.response?.data?.error || 'Gagal mendaftar', 'error')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await fetchAdminData()
  startCamera()
})

onUnmounted(() => {
  if (stream) stream.getTracks().forEach(t => t.stop())
  clearInterval(detectTimer)
})
</script>

<style scoped>
.admin-view { display: flex; flex-direction: column; gap: 2rem; }
.admin-stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; }
.admin-main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }
.admin-section { padding: 1.5rem; height: 100%; display: flex; flex-direction: column; gap: 1rem; }
.section-title { font-weight: 700; color: var(--gold-400); font-family: 'Rajdhani'; font-size: 1.3rem; border-bottom: 1px solid var(--glass-border); padding-bottom: .5rem; }
.section-desc { font-size: .8rem; color: var(--text-secondary); }

.manual-table-wrap { overflow-y: auto; max-height: 450px; }
.manual-table { width: 100%; border-collapse: collapse; }
.manual-table th { text-align: left; padding: .8rem; font-size: .75rem; color: var(--text-secondary); border-bottom: 2px solid var(--glass-border); text-transform: uppercase; }
.manual-table td { padding: 1rem .8rem; border-bottom: 1px solid rgba(212,160,23,.05); }

.s-name { font-weight: 700; font-size: .95rem; }
.s-nim { font-size: .75rem; color: var(--gold-400); font-weight: 600; }

.btn-group { display: flex; gap: .5rem; }
.mini-btn { padding: .4rem .8rem; border-radius: 6px; border: none; font-size: .7rem; font-weight: 800; cursor: pointer; transition: .2s; }
.mini-btn.ijin { background: rgba(245,158,11,.15); color: var(--warning); border: 1px solid var(--warning); }
.mini-btn.alfa { background: rgba(239,68,68,.15); color: var(--danger); border: 1px solid var(--danger); }
.mini-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.2); }
.mini-btn:disabled { opacity: .2; cursor: not-allowed; }

.reg-container { display: flex; flex-direction: column; gap: 1.2rem; }
.reg-video { width: 100%; aspect-ratio: 4/3; background: #000; border-radius: var(--radius-sm); object-fit: cover; border: 1px solid var(--glass-border); }
.reg-camera-box { position: relative; }
.cam-badge { position: absolute; bottom: 12px; left: 12px; background: rgba(5,10,20,.8); padding: .3rem .9rem; border-radius: 20px; font-size: .75rem; display: flex; align-items: center; gap: .5rem; border: 1px solid var(--gold-500); }
.dot { width: 10px; height: 10px; border-radius: 50%; background: #444; }
.dot.active { background: var(--success); box-shadow: 0 0 10px var(--success); }

/* Steps */
.reg-steps { display: flex; justify-content: space-between; gap: .8rem; margin-top: .5rem; }
.step-item { flex: 1; display: flex; flex-direction: column; align-items: center; gap: .4rem; padding: .6rem; border-radius: 12px; background: rgba(255,255,255,.05); border: 1px solid rgba(212,160,23,.1); }
.step-item.done { background: rgba(34,197,94,.1); border-color: var(--success); }
.step-item.done .step-num { background: var(--success); color: #fff; }
.step-num { width: 22px; height: 22px; border-radius: 50%; background: #333; font-size: .75rem; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.step-lbl { font-size: .65rem; color: var(--text-secondary); font-weight: 700; }
.step-item.done .step-lbl { color: var(--success); }

.btn-group-column { display: flex; flex-direction: column; gap: .8rem; }

@media (max-width: 1024px) {
  .admin-main-grid { grid-template-columns: 1fr; }
}
</style>
