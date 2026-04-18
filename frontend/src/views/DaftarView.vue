<template>
  <div class="daftar-view">
    <div class="panel-header">
      <h1>Daftar <span class="gold">Wajah Mahasiswa</span></h1>
      <p>Tambah mahasiswa baru — foto &amp; deskriptor wajah tersimpan di server</p>
    </div>

    <div class="reg-grid">
      <!-- ── Left: Camera + Form ─────────────── -->
      <div class="reg-left">
        <!-- Camera -->
        <div class="camera-frame" :class="{ 'frame-detected': faceDetected }">
          <video ref="videoRef" autoplay muted playsinline></video>
          <canvas ref="overlayRef" class="overlay-canvas"></canvas>
          <span class="corner tl"></span><span class="corner tr"></span>
          <span class="corner bl"></span><span class="corner br"></span>
          <div class="cam-pill">
            <span class="cam-dot" :class="{ 'dot-active': camActive, 'dot-detect': faceDetected }"></span>
            <span>{{ camStatus }}</span>
          </div>
          <!-- Face quality meter -->
          <div v-if="faceDetected" class="face-quality">
            <span class="fq-icon">✓</span> Wajah Terdeteksi — Siap Daftarkan
          </div>
        </div>
        <button class="btn-outline full-w" @click="startCamera" :disabled="camActive || loadingCam">
          {{ loadingCam ? '⏳…' : '🎥 Aktifkan Kamera Daftar' }}
        </button>

        <!-- Form -->
        <div class="reg-form glass-card">
          <div class="form-title">Data Mahasiswa</div>
          <div class="form-field">
            <label class="field-label">Nama Lengkap</label>
            <input
              v-model="form.name" class="field-input"
              placeholder="Contoh: Budi Santoso" maxlength="80"
            />
          </div>
          <div class="form-field">
            <label class="field-label">NIM</label>
            <input
              v-model="form.nim" class="field-input"
              placeholder="Contoh: 2023001234" maxlength="20"
            />
          </div>
          <div class="form-field">
            <label class="field-label">Program Studi / Divisi</label>
            <input
              v-model="form.prodi" class="field-input"
              placeholder="Contoh: Teknik Informatika" maxlength="60"
            />
          </div>
          <button
            class="btn-gold full-w"
            @click="captureAndRegister"
            :disabled="saving || !camActive"
          >
            {{ saving ? '⏳ Mendaftarkan…' : '📸 Ambil Foto & Daftarkan' }}
          </button>
        </div>

        <!-- Model loading -->
        <div v-if="loadingModels" class="model-bar">
          <div class="mb-fill" :style="{ width: modelPct + '%' }"></div>
          <span class="mb-label">Memuat model AI… {{ modelPct }}%</span>
        </div>
      </div>

      <!-- ── Right: Registered Students ────── -->
      <div class="reg-right glass-card">
        <div class="rr-header">
          <span class="rr-title">Mahasiswa Terdaftar</span>
          <span class="count-badge">{{ students.length }} orang</span>
        </div>

        <input
          v-model="search" class="field-input" style="margin-bottom:.8rem"
          placeholder="🔍 Cari nama atau NIM…"
        />

        <div v-if="!filteredStudents.length" class="empty-students">
          <div class="empty-icon">👤</div>
          <p>{{ search ? 'Tidak ditemukan' : 'Belum ada mahasiswa terdaftar' }}</p>
        </div>

        <div class="student-grid">
          <div
            v-for="st in filteredStudents" :key="st.nim"
            class="student-card"
          >
            <button class="del-btn" @click="deleteStudent(st.nim, st.name)" title="Hapus">✕</button>
            <div class="st-photo">
              <img v-if="st.photo_url" :src="st.photo_url" :alt="st.name" />
              <span v-else>{{ initials(st.name) }}</span>
            </div>
            <div class="st-name">{{ st.name }}</div>
            <div class="st-nim">{{ st.nim }}</div>
            <div class="st-prodi">{{ st.prodi || '—' }}</div>
            <div class="st-date">{{ fmtDate(st.registered_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'
import * as faceapi from '@vladmandic/face-api'
import axios from 'axios'

const toast = inject('toast')

const MODELS_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model'

// ── State ────────────────────────────────────────────────
const videoRef   = ref(null)
const overlayRef = ref(null)
const camActive  = ref(false)
const loadingCam = ref(false)
const faceDetected = ref(false)
const camStatus  = ref('Kamera belum aktif')

const modelsLoaded  = ref(false)
const loadingModels = ref(false)
const modelPct      = ref(0)

const students = ref([])
const search   = ref('')
const form     = ref({ name: '', nim: '', prodi: '' })
const saving   = ref(false)

let cameraStream = null
let detectTimer  = null

// ── Computed ─────────────────────────────────────────────
const filteredStudents = computed(() => {
  const q = search.value.toLowerCase()
  return students.value.filter(s =>
    !q || s.name.toLowerCase().includes(q) || s.nim.toLowerCase().includes(q)
  )
})

// ── Helpers ──────────────────────────────────────────────
const initials = name => (name || '?').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
const fmtDate  = iso  => iso ? new Date(iso).toLocaleDateString('id-ID', { day:'numeric', month:'short', year:'numeric' }) : '—'

// ── Load Models ──────────────────────────────────────────
const loadModels = async () => {
  if (modelsLoaded.value) return
  loadingModels.value = true; modelPct.value = 0
  try {
    await faceapi.nets.tinyFaceDetector.loadFromUri(MODELS_URL); modelPct.value = 33
    await faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_URL); modelPct.value = 66
    await faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL); modelPct.value = 100
    modelsLoaded.value = true
  } catch { toast('Gagal memuat model AI.', 'error') }
  finally { loadingModels.value = false }
}

// ── Load Students ────────────────────────────────────────
const loadStudents = async () => {
  const res = await axios.get('/api/students')
  students.value = res.data
}

// ── Camera ───────────────────────────────────────────────
const startCamera = async () => {
  await loadModels()
  if (!modelsLoaded.value) return
  loadingCam.value = true
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }, audio: false
    })
    videoRef.value.srcObject = cameraStream
    await videoRef.value.play()
    camActive.value  = true
    camStatus.value  = 'Kamera aktif — posisikan wajah'
    startFacePreview()
  } catch {
    toast('Kamera tidak dapat diakses.', 'error')
  } finally { loadingCam.value = false }
}

const startFacePreview = () => {
  clearInterval(detectTimer)
  detectTimer = setInterval(async () => {
    const vid = videoRef.value
    if (!vid || vid.readyState < 2) return
    const canvas = overlayRef.value
    canvas.width = vid.videoWidth; canvas.height = vid.videoHeight
    const opts = new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 })
    const det  = await faceapi.detectSingleFace(vid, opts).withFaceLandmarks()
    const ctx  = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    if (det) {
      faceDetected.value = true
      camStatus.value    = '✓ Wajah terdeteksi!'
      const b = det.detection.box
      ctx.strokeStyle = '#d4a017'; ctx.lineWidth = 2.5
      ctx.shadowColor = '#d4a017'; ctx.shadowBlur = 12
      ctx.strokeRect(b.x, b.y, b.width, b.height)
      ctx.shadowBlur = 0
    } else {
      faceDetected.value = false
      camStatus.value    = 'Tidak ada wajah — dekatkan'
    }
  }, 700)
}

// ── Capture & Register ───────────────────────────────────
const captureAndRegister = async () => {
  if (!form.value.name.trim()) { toast('Isi nama terlebih dahulu!', 'error'); return }
  if (!form.value.nim.trim())  { toast('Isi NIM terlebih dahulu!', 'error');  return }
  const vid = videoRef.value
  if (!vid || vid.readyState < 2) { toast('Kamera belum aktif.', 'error'); return }

  saving.value = true
  try {
    const opts = new faceapi.TinyFaceDetectorOptions({ inputSize: 320, scoreThreshold: 0.5 })
    const det  = await faceapi.detectSingleFace(vid, opts).withFaceLandmarks().withFaceDescriptor()
    if (!det) { toast('Tidak ada wajah terdeteksi. Posisikan wajah dengan jelas!', 'error'); return }

    // Crop face thumbnail 128×128
    const thumb = document.createElement('canvas')
    thumb.width = 128; thumb.height = 128
    const b = det.detection.box
    thumb.getContext('2d').drawImage(vid, b.x, b.y, b.width, b.height, 0, 0, 128, 128)
    const photoB64 = thumb.toDataURL('image/jpeg', 0.80)

    const payload = {
      name:       form.value.name.trim(),
      nim:        form.value.nim.trim(),
      prodi:      form.value.prodi.trim(),
      descriptor: Array.from(det.descriptor),
      photo:      photoB64
    }

    await axios.post('/api/students', payload)
    toast(`✓ ${payload.name} berhasil didaftarkan!`, 'success')
    form.value = { name: '', nim: '', prodi: '' }
    await loadStudents()
  } catch (err) {
    const msg = err.response?.data?.error || 'Gagal mendaftarkan mahasiswa.'
    toast(msg, 'error')
  } finally { saving.value = false }
}

// ── Delete Student ───────────────────────────────────────
const deleteStudent = async (nim, name) => {
  if (!confirm(`Hapus ${name} (${nim}) dari daftar? Data absensinya tetap tersimpan.`)) return
  await axios.delete(`/api/students/${nim}`)
  await loadStudents()
  toast(`${name} dihapus dari daftar.`, 'success')
}

// ── Lifecycle ────────────────────────────────────────────
onMounted(async () => {
  await loadModels()
  await loadStudents()
  await startCamera()
})
onUnmounted(() => {
  clearInterval(detectTimer)
  cameraStream?.getTracks().forEach(t => t.stop())
})
</script>

<style scoped>
.daftar-view { display: flex; flex-direction: column; gap: 1.4rem; }

/* Grid */
.reg-grid { display: grid; grid-template-columns: 420px 1fr; gap: 1.4rem; align-items: start; }

/* Left */
.reg-left { display: flex; flex-direction: column; gap: .85rem; }

/* Camera */
.camera-frame {
  position: relative; aspect-ratio: 4/3;
  background: var(--sky-800); border: 1px solid var(--glass-border);
  border-radius: var(--radius); overflow: hidden;
  transition: border-color .3s, box-shadow .3s;
}
.camera-frame video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.overlay-canvas    { position: absolute; inset: 0; width: 100%; height: 100%; }
.frame-detected    { border-color: var(--gold-500) !important; box-shadow: 0 0 24px var(--gold-glow) !important; }

.corner { position: absolute; width: 26px; height: 26px; border-color: var(--gold-400); border-style: solid; z-index: 5; }
.corner.tl { top: 9px;  left: 9px;  border-width: 2px 0 0 2px; border-radius: 3px 0 0 0; }
.corner.tr { top: 9px;  right: 9px; border-width: 2px 2px 0 0; border-radius: 0 3px 0 0; }
.corner.bl { bottom: 9px; left: 9px;  border-width: 0 0 2px 2px; border-radius: 0 0 0 3px; }
.corner.br { bottom: 9px; right: 9px; border-width: 0 2px 2px 0; border-radius: 0 0 3px 0; }

.face-quality {
  position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
  background: rgba(212,160,23,.88); color: var(--sky-900);
  font-size: .74rem; font-weight: 700; padding: .28rem .85rem;
  border-radius: 20px; white-space: nowrap; z-index: 10;
  animation: pulse-bar .8s ease-in-out infinite;
}
@keyframes pulse-bar { 0%,100%{ opacity:1; } 50%{ opacity:.75; } }

.cam-pill {
  position: absolute; bottom: 10px; left: 50%; transform: translateX(-50%);
  background: rgba(5,10,20,.78); backdrop-filter: blur(8px);
  border: 1px solid var(--glass-border); border-radius: 20px;
  padding: .25rem .85rem; display: flex; align-items: center; gap: .4rem;
  font-size: .74rem; z-index: 10; white-space: nowrap;
}
.cam-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); transition: var(--trans); }
.dot-active { background: var(--success); box-shadow: 0 0 7px var(--success); animation: blink .9s ease-in-out infinite; }
.dot-detect { background: var(--gold-400); box-shadow: 0 0 7px var(--gold-400); }
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:.35;} }

/* Form */
.reg-form { padding: 1.2rem; display: flex; flex-direction: column; gap: .85rem; }
.form-title { font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; font-weight: 700; color: var(--gold-400); letter-spacing: .04em; }
.form-field { display: flex; flex-direction: column; gap: .3rem; }

/* Model bar */
.model-bar { position: relative; height: 22px; background: var(--sky-700); border-radius: 20px; overflow: hidden; border: 1px solid var(--glass-border); }
.mb-fill   { height: 100%; background: linear-gradient(90deg, var(--gold-600), var(--gold-400)); transition: width .35s; }
.mb-label  { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: .7rem; font-weight: 700; color: var(--text-primary); }

/* Right */
.reg-right { padding: 1.2rem; display: flex; flex-direction: column; gap: .85rem; min-height: 400px; }
.rr-header { display: flex; align-items: center; justify-content: space-between; }
.rr-title  { font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; font-weight: 700; }
.count-badge { background: linear-gradient(135deg, var(--gold-400), var(--gold-600)); color: var(--sky-900); font-size: .7rem; font-weight: 700; padding: .2rem .7rem; border-radius: 20px; }

.empty-students { text-align: center; padding: 2.5rem 0; color: var(--text-muted); }
.empty-icon { font-size: 2.5rem; margin-bottom: .5rem; }

.student-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: .8rem; overflow-y: auto; max-height: 480px;
}
.student-card {
  background: var(--sky-700); border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm); padding: .9rem .6rem;
  display: flex; flex-direction: column; align-items: center; gap: .4rem;
  text-align: center; transition: var(--trans); position: relative;
}
.student-card:hover { border-color: var(--gold-500); box-shadow: 0 0 16px var(--gold-glow); transform: translateY(-2px); }
.del-btn {
  position: absolute; top: 5px; right: 5px;
  background: rgba(239,68,68,.15); border: 1px solid rgba(239,68,68,.3);
  color: var(--danger); border-radius: 5px; width: 20px; height: 20px;
  font-size: .65rem; cursor: pointer; display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: var(--trans);
}
.student-card:hover .del-btn { opacity: 1; }

.st-photo {
  width: 66px; height: 66px; border-radius: 50%;
  background: var(--sky-500); border: 2px solid var(--gold-500);
  box-shadow: 0 0 10px var(--gold-glow);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Rajdhani', sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--gold-400);
  overflow: hidden;
}
.st-photo img { width: 100%; height: 100%; object-fit: cover; }
.st-name  { font-size: .8rem; font-weight: 700; color: var(--text-primary); word-break: break-word; line-height: 1.2; }
.st-nim   { font-size: .7rem; color: var(--gold-400); font-weight: 600; }
.st-prodi { font-size: .65rem; color: var(--text-secondary); }
.st-date  { font-size: .62rem; color: var(--text-muted); }

@media (max-width: 960px) {
  .reg-grid { grid-template-columns: 1fr; }
}
</style>
