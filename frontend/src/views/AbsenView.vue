<template>
  <div class="absen-view">
    <!-- Panel header + mode toggle -->
    <div class="absen-header">
      <div>
        <h1 class="panel-header-title">Absensi <span class="gold">Wajah Otomatis</span></h1>
        <p class="panel-header-sub">Wajah terdeteksi → absen otomatis dalam 2 detik</p>
      </div>
      <div class="mode-toggle">
        <button
          :class="['mode-btn', mode === 'masuk' ? 'mode-masuk-active' : '']"
          @click="setMode('masuk')"
        >🟢 Absen Masuk</button>
        <button
          :class="['mode-btn', mode === 'pulang' ? 'mode-pulang-active' : '']"
          @click="setMode('pulang')"
        >🔴 Absen Pulang</button>
      </div>
    </div>

    <div class="scan-grid">
      <!-- ── Camera Column ─────────────────── -->
      <div class="camera-col">
        <div class="camera-frame" :class="{ 'frame-known': matchState === 'known', 'frame-unknown': matchState === 'unknown' }">
          <video ref="videoRef" autoplay muted playsinline></video>
          <canvas ref="overlayRef" class="overlay-canvas"></canvas>

          <!-- scan line -->
          <div class="scan-line" :class="{ active: cameraActive }"></div>

          <!-- corner accents -->
          <span class="corner tl"></span>
          <span class="corner tr"></span>
          <span class="corner bl"></span>
          <span class="corner br"></span>

          <!-- Confirm progress bar -->
          <div class="confirm-bar-wrap" v-show="confirmPct > 0">
            <div class="confirm-bar" :style="{ width: confirmPct + '%' }"></div>
            <span class="confirm-label">Mengkonfirmasi…{{ Math.round(confirmPct) }}%</span>
          </div>

          <!-- status pill -->
          <div class="cam-pill">
            <span class="cam-dot" :class="{ 'dot-active': cameraActive, 'dot-detect': matchState === 'known' }"></span>
            <span>{{ statusText }}</span>
          </div>
        </div>

        <!-- controls -->
        <div class="cam-controls">
          <button class="btn-gold" @click="startCamera" :disabled="cameraActive || loadingModels">
            <span>{{ loadingModels ? '⏳ Memuat AI…' : '▶ Aktifkan Kamera' }}</span>
          </button>
          <button class="btn-outline" @click="stopCamera" :disabled="!cameraActive">⏹ Stop</button>
        </div>

        <!-- Model load progress -->
        <div v-if="loadingModels" class="model-load-bar">
          <div class="mlb-fill" :style="{ width: modelLoadPct + '%' }"></div>
          <span class="mlb-label">Memuat model AI… {{ modelLoadPct }}%</span>
        </div>
      </div>

      <!-- ── Info Column ──────────────────── -->
      <div class="info-col">
        <!-- Detection Result Card -->
        <div class="detect-card glass-card" :class="detectCardClass">
          <div class="detect-avatar">
            <img v-if="currentPerson?.photo_url" :src="currentPerson.photo_url" :alt="currentPerson.name" />
            <span v-else-if="currentPerson">{{ initials(currentPerson.name) }}</span>
            <span v-else class="avatar-question">?</span>
          </div>
          <div class="detect-body">
            <div class="detect-name">{{ currentPerson?.name || 'Menunggu Wajah…' }}</div>
            <div class="detect-nim" v-if="currentPerson">NIM · {{ currentPerson.nim }}</div>
            <div class="detect-hint" v-else>Aktifkan kamera &amp; dekatkan wajah</div>
            <div class="detect-status" v-if="alreadyAbsen">
              ✓ Sudah absen {{ mode }} hari ini
            </div>
          </div>
          <span :class="['badge', detectBadgeClass]">{{ detectBadgeText }}</span>
        </div>

        <!-- Mini Stats -->
        <div class="mini-stats">
          <div class="mini-stat">
            <div class="ms-val">{{ todayMasukCount }}</div>
            <div class="ms-lbl">Masuk Hari Ini</div>
          </div>
          <div class="mini-stat">
            <div class="ms-val">{{ todayPulangCount }}</div>
            <div class="ms-lbl">Pulang Hari Ini</div>
          </div>
          <div class="mini-stat">
            <div class="ms-val">{{ students.length }}</div>
            <div class="ms-lbl">Terdaftar</div>
          </div>
        </div>

        <!-- Today's Log -->
        <div class="today-log glass-card">
          <div class="log-title">
            📋 Log Hari Ini
            <span class="log-count-badge">{{ todayLog.length }}</span>
          </div>
          <div class="log-scroll">
            <div v-if="!todayLog.length" class="empty-msg">Belum ada absensi hari ini</div>
            <TransitionGroup name="log-anim" tag="div">
              <div v-for="rec in todayLog" :key="rec.id" class="log-item">
                <div class="log-av">
                  <img v-if="photoFor(rec.nim)" :src="photoFor(rec.nim)" :alt="rec.name" />
                  <span v-else>{{ initials(rec.name) }}</span>
                </div>
                <div class="log-info">
                  <div class="log-name">{{ rec.name }}</div>
                  <div class="log-nim">{{ rec.nim }}</div>
                </div>
                <span :class="['badge', rec.type === 'masuk' ? 'badge-masuk' : 'badge-pulang']">
                  {{ rec.type === 'masuk' ? 'Masuk' : 'Pulang' }}
                </span>
                <span class="log-time">{{ rec.time }}</span>
              </div>
            </TransitionGroup>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Success Overlay ─────────────────────── -->
    <Transition name="success-flash">
      <div v-if="showSuccess" class="success-overlay" @click="showSuccess = false">
        <div class="success-card">
          <div class="success-star">✦</div>
          <h2>Absen {{ successRec?.type === 'masuk' ? 'Masuk' : 'Pulang' }} Berhasil!</h2>
          <p class="suc-name">{{ successRec?.name }}</p>
          <div class="suc-meta">
            <span>NIM: <b>{{ successRec?.nim }}</b></span>
            <span>{{ successRec?.time }}</span>
          </div>
          <span :class="['badge', successRec?.type === 'masuk' ? 'badge-masuk' : 'badge-pulang']" style="font-size:.85rem;padding:.4rem 1rem">
            {{ successRec?.type === 'masuk' ? '✓ MASUK' : '✓ PULANG' }}
          </span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, watch } from 'vue'
import * as faceapi from '@vladmandic/face-api'
import axios from 'axios'

const toast = inject('toast')

// ── Models ─────────────────────────────────────────────
const MODELS_URL   = '/models_fix'
const CONFIRM_MS   = 1500   // ms before auto-record
const COOLDOWN_MS  = 40000  // prevent re-trigger same person+mode
const DETECT_EVERY = 500    // ms between detection frames
const MATCH_THR    = 0.50   // FaceMatcher distance threshold

// ── State ───────────────────────────────────────────────
const videoRef    = ref(null)
const overlayRef  = ref(null)

const modelsLoaded  = ref(false)
const loadingModels = ref(false)
const modelLoadPct  = ref(0)

const cameraActive  = ref(false)
const mode          = ref('masuk')

const students      = ref([])
const faceMatcher   = ref(null)

const currentPerson = ref(null)   // matched student object
const matchState    = ref('idle') // idle | unknown | known
const alreadyAbsen  = ref(false)
const confirmPct    = ref(0)

const todayLog      = ref([])
const showSuccess   = ref(false)
const successRec    = ref(null)

const cooldowns     = {}           // nim_type → timestamp
let   cameraStream  = null
let   detectTimer   = null
let   confirmStart  = null

// ── Computed ────────────────────────────────────────────
const statusText = computed(() => {
  if (loadingModels.value) return 'Memuat model AI…'
  if (!cameraActive.value) return 'Kamera tidak aktif'
  if (matchState.value === 'known') return `Dikenal: ${currentPerson.value?.name}`
  if (matchState.value === 'unknown') return 'Wajah tidak dikenal'
  return 'Menunggu wajah…'
})
const detectCardClass = computed(() => {
  if (matchState.value === 'known' && !alreadyAbsen.value) return 'card-known'
  if (matchState.value === 'known' && alreadyAbsen.value)  return 'card-already'
  if (matchState.value === 'unknown') return 'card-unknown'
  return ''
})
const detectBadgeClass = computed(() => {
  if (matchState.value === 'known')    return alreadyAbsen.value ? 'badge-asing' : 'badge-masuk'
  if (matchState.value === 'unknown')  return 'badge-asing'
  return ''
})
const detectBadgeText = computed(() => {
  if (matchState.value === 'known')   return alreadyAbsen.value ? 'SUDAH ABSEN' : 'DIKENAL'
  if (matchState.value === 'unknown') return 'TIDAK DIKENAL'
  return '—'
})
const todayMasukCount  = computed(() => todayLog.value.filter(r => r.type === 'masuk').length)
const todayPulangCount = computed(() => todayLog.value.filter(r => r.type === 'pulang').length)

// ── Helpers ─────────────────────────────────────────────
const initials  = name => (name || '?').split(' ').map(w => w[0]).join('').toUpperCase().slice(0,2)
const photoFor  = nim  => students.value.find(s => s.nim === nim)?.photo_url || null
const cooldownKey = (nim, t) => `${nim}_${t}`
const inCooldown  = (nim, t) => {
  const k = cooldownKey(nim, t)
  return cooldowns[k] && (Date.now() - cooldowns[k] < COOLDOWN_MS)
}
const today = () => new Date().toISOString().slice(0, 10)

// ── Load Students + build FaceMatcher ───────────────────
const loadStudents = async () => {
  const res = await axios.get('/api/students')
  students.value = res.data
  buildMatcher()
}

const buildMatcher = () => {
  const valid = students.value.filter(s => Array.isArray(s.descriptors) && s.descriptors.length)
  if (!valid.length) { faceMatcher.value = null; return }
  
  const labeled = valid.map(s => {
    // Map each descriptor array to a Float32Array
    const descList = s.descriptors.map(d => new Float32Array(d))
    return new faceapi.LabeledFaceDescriptors(s.nim, descList)
  })
  faceMatcher.value = new faceapi.FaceMatcher(labeled, MATCH_THR)
}

// ── Load Today Log ───────────────────────────────────────
const loadTodayLog = async () => {
  const res = await axios.get('/api/attendance', { params: { date: today() } })
  todayLog.value = res.data.slice().reverse()
}

// ── Load AI Models ───────────────────────────────────────
const loadModels = async () => {
  if (modelsLoaded.value) return
  loadingModels.value = true
  modelLoadPct.value  = 0
  try {
    await faceapi.nets.ssdMobilenetv1.loadFromUri(MODELS_URL)
    modelLoadPct.value = 33
    await faceapi.nets.faceLandmark68Net.loadFromUri(MODELS_URL)
    modelLoadPct.value = 66
    await faceapi.nets.faceRecognitionNet.loadFromUri(MODELS_URL)
    modelLoadPct.value = 100
    modelsLoaded.value = true
    toast('✓ Model AI berhasil dimuat', 'success')
  } catch (e) {
    toast('Gagal memuat model AI. Cek koneksi internet.', 'error')
    console.error(e)
  } finally {
    loadingModels.value = false
  }
}

// ── Camera ───────────────────────────────────────────────
const startCamera = async () => {
  await loadModels()
  if (!modelsLoaded.value) return
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
      audio: false
    })
    const vid = videoRef.value
    vid.srcObject = cameraStream
    await vid.play()
    cameraActive.value = true
    toast('Kamera aktif — menunggu wajah…', 'success')
    startDetectionLoop()
  } catch (err) {
    toast('Izin kamera ditolak atau tidak tersedia.', 'error')
  }
}

const stopCamera = () => {
  clearInterval(detectTimer)
  cameraStream?.getTracks().forEach(t => t.stop())
  cameraStream    = null
  cameraActive.value = false
  matchState.value   = 'idle'
  currentPerson.value = null
  confirmPct.value   = 0
  confirmStart       = null
  const ctx = overlayRef.value?.getContext('2d')
  ctx?.clearRect(0, 0, overlayRef.value.width, overlayRef.value.height)
}

// ── Detection Loop ───────────────────────────────────────
const startDetectionLoop = () => {
  clearInterval(detectTimer)
  detectTimer = setInterval(runDetection, DETECT_EVERY)
}

const runDetection = async () => {
  const vid = videoRef.value
  if (!vid || vid.readyState < 2 || !modelsLoaded.value) return

  const canvas = overlayRef.value
  const dW = vid.videoWidth, dH = vid.videoHeight
  canvas.width  = dW
  canvas.height = dH

  const opts       = new faceapi.SsdMobilenetv1Options({ minConfidence: 0.5 })
  const detections = await faceapi.detectAllFaces(vid, opts).withFaceLandmarks().withFaceDescriptors()

  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, dW, dH)

  if (!detections.length) {
    resetMatch()
    return
  }

  // Use first detected face
  const det = detections[0]
  const box = det.detection.box

  let matchedNim = null, matchedStudent = null
  if (faceMatcher.value) {
    const result = faceMatcher.value.findBestMatch(det.descriptor)
    if (result.distance < MATCH_THR) {
      matchedNim     = result.label
      matchedStudent = students.value.find(s => s.nim === matchedNim) || null
    }
  }

  const isKnown = !!matchedStudent

  // Draw face box
  ctx.strokeStyle = isKnown ? '#22c55e' : '#d4a017'
  ctx.lineWidth   = 2.5
  ctx.shadowColor = ctx.strokeStyle
  ctx.shadowBlur  = 14
  ctx.strokeRect(box.x, box.y, box.width, box.height)
  ctx.shadowBlur  = 0

  // Label background + text
  const label  = isKnown ? `${matchedStudent.name}` : 'Tidak Dikenal'
  const labelW = ctx.measureText(label).width + 16
  ctx.fillStyle = isKnown ? 'rgba(34,197,94,.82)' : 'rgba(212,160,23,.82)'
  ctx.fillRect(box.x, box.y - 26, Math.min(labelW, box.width + 40), 26)
  ctx.fillStyle = '#000'
  ctx.font      = 'bold 12px Outfit, sans-serif'
  ctx.fillText(label, box.x + 7, box.y - 8)

  if (isKnown) {
    handleKnownFace(matchedStudent)
  } else {
    matchState.value    = 'unknown'
    currentPerson.value = null
    alreadyAbsen.value  = false
    resetConfirm()
  }
}

// ── Handle known face → auto confirm ────────────────────
const handleKnownFace = (student) => {
  currentPerson.value = student
  matchState.value    = 'known'

  const already = inCooldown(student.nim, mode.value)
  alreadyAbsen.value = already

  if (already) {
    resetConfirm()
    return
  }

  // First frame for this person?
  if (!confirmStart || (confirmStart.nim !== student.nim)) {
    confirmStart = { nim: student.nim, ts: Date.now() }
  }

  const elapsed   = Date.now() - confirmStart.ts
  confirmPct.value = Math.min(100, (elapsed / CONFIRM_MS) * 100)

  if (confirmPct.value >= 100) {
    triggerAttendance(student)
  }
}

const resetMatch = () => {
  matchState.value    = 'idle'
  currentPerson.value = null
  alreadyAbsen.value  = false
  resetConfirm()
}

const resetConfirm = () => {
  confirmPct.value = 0
  confirmStart     = null
}

// ── Record Attendance ────────────────────────────────────
const triggerAttendance = async (student) => {
  // Set cooldown immediately to prevent double-fire
  cooldowns[cooldownKey(student.nim, mode.value)] = Date.now()
  resetConfirm()

  try {
    const res = await axios.post('/api/attendance', {
      nim:  student.nim,
      name: student.name,
      type: mode.value
    })
    const rec = res.data.record
    todayLog.value.unshift(rec)
    successRec.value  = rec
    showSuccess.value = true
    setTimeout(() => { showSuccess.value = false }, 3500)
    toast(`✓ ${student.name} — absen ${mode.value} berhasil!`, 'success')
  } catch (err) {
    if (err.response?.status === 409) {
      alreadyAbsen.value = true
      toast(`${student.name} sudah absen ${mode.value} hari ini`, 'warning')
    } else {
      toast('Gagal menyimpan absensi. Cek koneksi backend.', 'error')
    }
  }
}

// ── Mode switch ──────────────────────────────────────────
const setMode = (m) => { mode.value = m; resetMatch() }

// ── Watch mode to reset state ────────────────────────────
watch(mode, () => {
  alreadyAbsen.value  = false
  currentPerson.value = null
  matchState.value    = 'idle'
  resetConfirm()
})

// ── Lifecycle ────────────────────────────────────────────
onMounted(async () => {
  await loadModels()
  await loadStudents()
  await loadTodayLog()
})
onUnmounted(() => stopCamera())
</script>

<style scoped>
.absen-view { display: flex; flex-direction: column; gap: 1.4rem; }

/* ── Header ───────────────────────────────── */
.absen-header {
  display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 1rem;
}
.panel-header-title {
  font-family: 'Rajdhani', sans-serif; font-size: 1.85rem; font-weight: 700; letter-spacing: .02em;
}
.panel-header-sub { color: var(--text-secondary); font-size: .84rem; margin-top: .25rem; }

/* ── Mode Toggle ──────────────────────────── */
.mode-toggle { display: flex; gap: .6rem; }
.mode-btn {
  padding: .65rem 1.4rem; border-radius: 30px;
  border: 1px solid rgba(212,160,23,.25); background: var(--sky-700);
  color: var(--text-secondary); font-family: 'Outfit', sans-serif;
  font-size: .88rem; font-weight: 600; cursor: pointer; transition: var(--trans);
}
.mode-masuk-active {
  background: rgba(34,197,94,.14) !important;
  border-color: var(--success) !important; color: var(--success) !important;
  box-shadow: 0 0 16px rgba(34,197,94,.2);
}
.mode-pulang-active {
  background: rgba(239,68,68,.12) !important;
  border-color: var(--danger) !important; color: var(--danger) !important;
  box-shadow: 0 0 16px rgba(239,68,68,.15);
}

/* ── Grid ─────────────────────────────────── */
.scan-grid {
  display: grid; grid-template-columns: minmax(0,1fr) 360px;
  gap: 1.4rem; align-items: start;
}

/* ── Camera Frame ─────────────────────────── */
.camera-col { display: flex; flex-direction: column; gap: .9rem; }
.camera-frame {
  position: relative; aspect-ratio: 4/3;
  background: var(--sky-800);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: 0 0 40px rgba(212,160,23,.06), inset 0 0 60px rgba(5,10,20,.5);
  transition: border-color .3s ease, box-shadow .3s ease;
}
.camera-frame video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.camera-frame .overlay-canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
.frame-known  { border-color: var(--success) !important; box-shadow: 0 0 30px rgba(34,197,94,.18) !important; }
.frame-unknown{ border-color: var(--gold-500) !important; box-shadow: 0 0 25px rgba(212,160,23,.15) !important; }

/* corners */
.corner { position: absolute; width: 28px; height: 28px; border-color: var(--gold-400); border-style: solid; pointer-events: none; z-index: 5; }
.corner.tl { top: 10px;  left: 10px;  border-width: 2px 0 0 2px; border-radius: 4px 0 0 0; }
.corner.tr { top: 10px;  right: 10px; border-width: 2px 2px 0 0; border-radius: 0 4px 0 0; }
.corner.bl { bottom: 10px; left: 10px;  border-width: 0 0 2px 2px; border-radius: 0 0 0 4px; }
.corner.br { bottom: 10px; right: 10px; border-width: 0 2px 2px 0; border-radius: 0 0 4px 0; }

/* scan line */
.scan-line { position: absolute; left: 0; right: 0; height: 2px; background: linear-gradient(90deg,transparent,var(--gold-400),transparent); box-shadow: 0 0 8px var(--gold-500); top: 0; opacity: 0; pointer-events: none; z-index: 4; }
.scan-line.active { opacity: 1; animation: scanAnim 2.2s linear infinite; }
@keyframes scanAnim { 0% { top: 0; } 100% { top: 100%; } }

/* confirm progress */
.confirm-bar-wrap {
  position: absolute; bottom: 0; left: 0; right: 0; z-index: 6;
  height: 6px; background: rgba(5,10,20,.6);
}
.confirm-bar {
  height: 100%; background: linear-gradient(90deg, var(--success), var(--gold-400));
  box-shadow: 0 0 10px var(--success); transition: width .1s linear;
}
.confirm-label {
  position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
  background: rgba(5,10,20,.85); border-radius: 20px; padding: .2rem .7rem;
  font-size: .72rem; color: var(--gold-400); white-space: nowrap;
  font-weight: 700; letter-spacing: .04em;
}

/* cam pill */
.cam-pill {
  position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
  background: rgba(5,10,20,.78); backdrop-filter: blur(8px);
  border: 1px solid var(--glass-border); border-radius: 20px;
  padding: .28rem .9rem; display: flex; align-items: center; gap: .4rem;
  font-size: .76rem; z-index: 10; white-space: nowrap;
}
.cam-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); transition: var(--trans); }
.dot-active { background: var(--success); box-shadow: 0 0 7px var(--success); animation: blink .9s ease-in-out infinite; }
.dot-detect { background: var(--gold-400); box-shadow: 0 0 7px var(--gold-400); }
@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:.35; } }

.cam-controls { display: flex; gap: .7rem; }

/* model load bar */
.model-load-bar {
  position: relative; height: 24px;
  background: var(--sky-700); border-radius: 20px; overflow: hidden;
  border: 1px solid var(--glass-border);
}
.mlb-fill { height: 100%; background: linear-gradient(90deg, var(--gold-500), var(--gold-400)); transition: width .4s ease; }
.mlb-label { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: .72rem; font-weight: 700; color: var(--text-primary); }

/* ── Info Column ──────────────────────────── */
.info-col { display: flex; flex-direction: column; gap: .9rem; }

/* Detection card */
.detect-card {
  display: flex; align-items: center; gap: .9rem; padding: 1.1rem;
  transition: border-color .3s, box-shadow .3s;
}
.card-known   { border-color: var(--success) !important; box-shadow: 0 0 20px rgba(34,197,94,.15) !important; }
.card-already { border-color: var(--warning) !important; box-shadow: 0 0 16px rgba(245,158,11,.12) !important; }
.card-unknown { border-color: var(--gold-500) !important; }

.detect-avatar {
  width: 54px; height: 54px; border-radius: 50%; flex-shrink: 0;
  background: var(--sky-600); border: 2px solid var(--glass-border);
  display: flex; align-items: center; justify-content: center;
  font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; font-weight: 700; color: var(--gold-400);
  overflow: hidden;
}
.detect-avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-question { font-size: 1.6rem; color: var(--text-muted); }
.detect-body { flex: 1; min-width: 0; }
.detect-name { font-weight: 700; font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.detect-nim  { font-size: .78rem; color: var(--text-secondary); margin-top: .15rem; }
.detect-hint { font-size: .78rem; color: var(--text-muted); margin-top: .15rem; }
.detect-status { font-size: .74rem; color: var(--warning); margin-top: .25rem; font-weight: 600; }

/* Mini stats */
.mini-stats { display: grid; grid-template-columns: repeat(3,1fr); gap: .7rem; }
.mini-stat {
  background: var(--glass); border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm); padding: .85rem .5rem; text-align: center;
}
.ms-val { font-family: 'Rajdhani', sans-serif; font-size: 1.55rem; font-weight: 700; color: var(--gold-400); }
.ms-lbl { font-size: .64rem; color: var(--text-secondary); margin-top: .15rem; line-height: 1.2; }

/* Today log */
.today-log { padding: 1rem; display: flex; flex-direction: column; gap: .6rem; flex: 1; }
.log-title { font-size: .8rem; font-weight: 700; color: var(--gold-400); letter-spacing: .05em; display: flex; align-items: center; gap: .5rem; }
.log-count-badge {
  background: var(--gold-500); color: var(--sky-900);
  font-size: .68rem; font-weight: 700; padding: .1rem .5rem; border-radius: 20px;
}
.log-scroll { display: flex; flex-direction: column; gap: .4rem; max-height: 280px; overflow-y: auto; }
.empty-msg { color: var(--text-muted); font-size: .82rem; text-align: center; padding: 1rem 0; }
.log-item {
  display: flex; align-items: center; gap: .65rem; padding: .55rem .4rem;
  border-bottom: 1px solid rgba(212,160,23,.05); font-size: .81rem;
}
.log-item:last-child { border-bottom: none; }
.log-av {
  width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
  background: var(--sky-500); border: 1px solid var(--glass-border);
  display: flex; align-items: center; justify-content: center;
  font-size: .8rem; font-weight: 700; color: var(--gold-400); overflow: hidden;
}
.log-av img { width: 100%; height: 100%; object-fit: cover; }
.log-info { flex: 1; min-width: 0; }
.log-name { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.log-nim  { font-size: .68rem; color: var(--text-secondary); }
.log-time { font-size: .7rem; color: var(--text-muted); flex-shrink: 0; }

/* log animation */
.log-anim-enter-active { transition: all .3s ease; }
.log-anim-enter-from   { opacity: 0; transform: translateX(20px); }

/* ── Success Overlay ──────────────────────── */
.success-overlay {
  position: fixed; inset: 0; z-index: 500;
  background: rgba(5,10,20,.72); backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
}
.success-card {
  background: linear-gradient(145deg, var(--sky-700), var(--sky-800));
  border: 1px solid var(--gold-500);
  border-radius: 22px; padding: 2.5rem 2rem; text-align: center;
  max-width: 360px; width: 92%;
  box-shadow: 0 0 60px var(--gold-glow), 0 20px 60px rgba(5,10,20,.6);
  display: flex; flex-direction: column; align-items: center; gap: .75rem;
  animation: cardBounce .4s cubic-bezier(.34,1.56,.64,1);
}
@keyframes cardBounce { from { opacity:0; transform: scale(.8); } to { opacity:1; transform: scale(1); } }
.success-star {
  font-size: 3.2rem; color: var(--gold-400);
  text-shadow: 0 0 28px var(--gold-glow);
  animation: pulse-icon 1.5s ease-in-out infinite;
}
.success-card h2 { font-family: 'Rajdhani', sans-serif; font-size: 1.6rem; font-weight: 700; }
.suc-name { font-size: 1.2rem; font-weight: 700; color: var(--gold-400); }
.suc-meta { display: flex; gap: 1.2rem; font-size: .82rem; color: var(--text-secondary); }
.success-flash-enter-active, .success-flash-leave-active { transition: opacity .3s ease; }
.success-flash-enter-from, .success-flash-leave-to { opacity: 0; }

/* ── Responsive ───────────────────────────── */
@media (max-width: 900px) {
  .scan-grid { grid-template-columns: 1fr; }
  .absen-header { flex-direction: column; }
}
</style>
