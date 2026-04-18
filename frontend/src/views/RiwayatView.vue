<template>
  <div class="riwayat-view">
    <div class="panel-header">
      <h1>Riwayat <span class="gold">Absensi</span></h1>
      <p>Rekap lengkap absensi masuk &amp; pulang per mahasiswa</p>
    </div>

    <!-- Filters -->
    <div class="filter-bar glass-card">
      <div class="filter-field">
        <label class="field-label">Tanggal</label>
        <input type="date" v-model="filterDate" class="field-input" @change="loadData" />
      </div>
      <div class="filter-field" style="flex:1">
        <label class="field-label">Cari Nama / NIM</label>
        <input v-model="filterName" class="field-input" placeholder="Ketik nama atau NIM…" @input="applyFilter" />
      </div>
      <div class="filter-field">
        <label class="field-label">Mode</label>
        <select v-model="filterMode" class="field-input" @change="applyFilter">
          <option value="">Semua</option>
          <option value="masuk">Masuk</option>
          <option value="pulang">Pulang</option>
        </select>
      </div>
      <div class="filter-actions">
        <button class="btn-gold" @click="exportCSV">⬇ CSV</button>
        <button class="btn-danger" @click="clearAll">🗑 Hapus Semua</button>
      </div>
    </div>

    <!-- Summary pills -->
    <div class="summary-pills">
      <div class="pill">
        <span class="pill-val">{{ summaryMasuk }}</span>
        <span class="pill-lbl">Absen Masuk</span>
      </div>
      <div class="pill">
        <span class="pill-val">{{ summaryPulang }}</span>
        <span class="pill-lbl">Absen Pulang</span>
      </div>
      <div class="pill">
        <span class="pill-val">{{ uniqueStudents }}</span>
        <span class="pill-lbl">Mahasiswa Hadir</span>
      </div>
    </div>

    <!-- Table -->
    <div v-if="loading" class="table-loading">
      <div class="spinner"></div> Memuat data…
    </div>

    <div v-else-if="!rows.length" class="empty-state">
      <div class="es-icon">📋</div>
      <p>Tidak ada data absensi{{ filterDate ? ` pada ${fmtDisplayDate(filterDate)}` : '' }}</p>
    </div>

    <div v-else class="table-wrap">
      <table class="att-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Foto</th>
            <th>Nama</th>
            <th>NIM</th>
            <th>Status</th>
            <th>Mode</th>
            <th>Tanggal</th>
            <th>Waktu</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(rec, i) in rows" :key="rec.id">
            <td class="td-num">{{ i + 1 }}</td>
            <td>
              <div class="tbl-av">
                <img v-if="photoFor(rec.nim)" :src="photoFor(rec.nim)" :alt="rec.name" />
                <span v-else>{{ initials(rec.name) }}</span>
              </div>
            </td>
            <td class="td-name">{{ rec.name }}</td>
            <td class="td-nim">{{ rec.nim }}</td>
            <td>
              <span :class="['badge', rec.status === 'hadir' ? 'badge-masuk' : (rec.status === 'ijin' ? 'badge-pulang' : 'badge-asing')]">
                {{ rec.status.toUpperCase() }}
              </span>
            </td>
            <td>
              <span v-if="rec.status === 'hadir'" class="mode-text">
                {{ rec.type === 'masuk' ? 'IN' : 'OUT' }}
              </span>
              <span v-else>—</span>
            </td>
            <td class="td-date">{{ rec.date }}</td>
            <td class="td-time">{{ rec.time }}</td>
            <td>
              <button class="row-del-btn" @click="deleteRecord(rec.id)" title="Hapus">✕</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination info -->
    <div v-if="rows.length" class="table-footer">
      Menampilkan {{ rows.length }} record
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted } from 'vue'
import axios from 'axios'

const toast = inject('toast')

const filterDate = ref(today())
const filterName = ref('')
const filterMode = ref('')
const loading    = ref(false)

const allRows  = ref([])   // raw from backend
const rows     = ref([])   // after local filter
const students = ref([])   // for photos

// ── Computed ─────────────────────────────────────────────
const summaryMasuk    = computed(() => rows.value.filter(r => r.type === 'masuk').length)
const summaryPulang   = computed(() => rows.value.filter(r => r.type === 'pulang').length)
const uniqueStudents  = computed(() => new Set(rows.value.filter(r => r.type === 'masuk').map(r => r.nim)).size)

// ── Helpers ──────────────────────────────────────────────
function today() { return new Date().toISOString().slice(0,10) }
const initials  = name => (name||'?').split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2)
const photoFor  = nim  => students.value.find(s => s.nim === nim)?.photo_url || null
const fmtDisplayDate = iso => iso ? new Date(iso+'T00:00:00').toLocaleDateString('id-ID',{weekday:'long',day:'numeric',month:'long',year:'numeric'}) : ''

// ── Load ─────────────────────────────────────────────────
const loadData = async () => {
  loading.value = true
  try {
    const [attRes, stRes] = await Promise.all([
      axios.get('/api/attendance', { params: { date: filterDate.value } }),
      axios.get('/api/students')
    ])
    allRows.value  = attRes.data
    students.value = stRes.data
    applyFilter()
  } catch { toast('Gagal memuat data.', 'error') }
  finally { loading.value = false }
}

const applyFilter = () => {
  const q = filterName.value.toLowerCase()
  const m = filterMode.value
  rows.value = allRows.value.filter(r => {
    if (q && !r.name.toLowerCase().includes(q) && !r.nim.toLowerCase().includes(q)) return false
    if (m && r.type !== m) return false
    return true
  })
}

// ── Delete single record ─────────────────────────────────
const deleteRecord = async (id) => {
  if (!confirm('Hapus record ini?')) return
  await axios.delete(`/api/attendance/${id}`)
  await loadData()
  toast('Record dihapus.', 'success')
}

// ── Clear all ────────────────────────────────────────────
const clearAll = async () => {
  if (!confirm('Hapus SEMUA riwayat absensi? Tindakan ini tidak dapat dibatalkan.')) return
  await axios.delete('/api/attendance/clear')
  await loadData()
  toast('Semua riwayat dihapus.', 'success')
}

// ── Export CSV ───────────────────────────────────────────
const exportCSV = () => {
  if (!rows.value.length) { toast('Tidak ada data untuk diekspor.', 'error'); return }
  const header = 'No,Nama,NIM,Mode,Tanggal,Waktu'
  const body   = rows.value.map((r,i) =>
    `${i+1},"${r.name}","${r.nim}","${r.type}","${r.date}","${r.time}"`
  )
  const csv  = [header, ...body].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url  = URL.createObjectURL(blob)
  const a    = Object.assign(document.createElement('a'), { href: url, download: `absensi_${filterDate.value}.csv` })
  a.click(); URL.revokeObjectURL(url)
  toast('CSV berhasil diunduh!', 'success')
}

onMounted(loadData)
</script>

<style scoped>
.riwayat-view { display: flex; flex-direction: column; gap: 1.2rem; }

/* Filter bar */
.filter-bar {
  display: flex; align-items: flex-end; gap: .85rem; padding: 1.1rem 1.2rem; flex-wrap: wrap;
}
.filter-field { display: flex; flex-direction: column; gap: .3rem; min-width: 140px; }
.filter-actions { display: flex; gap: .55rem; align-items: center; margin-top: auto; }

select.field-input { cursor: pointer; }

/* Summary pills */
.summary-pills { display: flex; gap: .75rem; flex-wrap: wrap; }
.pill {
  background: var(--glass); border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm); padding: .7rem 1.2rem;
  display: flex; flex-direction: column; align-items: center; gap: .15rem;
  min-width: 110px;
}
.pill-val { font-family: 'Rajdhani', sans-serif; font-size: 1.6rem; font-weight: 700; color: var(--gold-400); }
.pill-lbl { font-size: .68rem; color: var(--text-secondary); }

/* Loading */
.table-loading {
  display: flex; align-items: center; gap: .75rem;
  justify-content: center; padding: 3rem; color: var(--text-secondary);
}
.spinner {
  width: 22px; height: 22px; border: 2px solid rgba(212,160,23,.2);
  border-top-color: var(--gold-400); border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Empty */
.empty-state { text-align: center; padding: 3rem; color: var(--text-muted); }
.es-icon { font-size: 2.8rem; margin-bottom: .5rem; }

/* Table */
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--glass-border); border-radius: var(--radius);
}
.att-table { width: 100%; border-collapse: collapse; font-size: .83rem; }
.att-table thead { background: rgba(212,160,23,.07); }
.att-table th {
  padding: .8rem 1rem; text-align: left; white-space: nowrap;
  font-size: .7rem; font-weight: 700; letter-spacing: .07em; color: var(--gold-400);
  border-bottom: 1px solid var(--glass-border);
}
.att-table td { padding: .65rem 1rem; border-bottom: 1px solid rgba(212,160,23,.04); vertical-align: middle; }
.att-table tbody tr:hover { background: var(--glass-hover); }
.att-table tbody tr:last-child td { border-bottom: none; }

.td-num  { color: var(--text-muted); width: 42px; }
.td-name { font-weight: 600; }
.td-nim  { color: var(--gold-400); font-size: .78rem; font-weight: 600; }
.td-date { color: var(--text-secondary); }
.td-time { color: var(--gold-400); font-family: 'Rajdhani', sans-serif; font-weight: 600; font-size: .92rem; }

.tbl-av {
  width: 34px; height: 34px; border-radius: 50%;
  background: var(--sky-500); border: 1px solid var(--glass-border);
  display: flex; align-items: center; justify-content: center;
  font-size: .78rem; font-weight: 700; color: var(--gold-400); overflow: hidden;
}
.tbl-av img { width: 100%; height: 100%; object-fit: cover; }

.row-del-btn {
  background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3);
  color: var(--danger); border-radius: 5px; width: 24px; height: 24px;
  font-size: .7rem; cursor: pointer; transition: var(--trans);
}
.row-del-btn:hover { background: rgba(239,68,68,.25); }

.table-footer {
  font-size: .78rem; color: var(--text-muted); text-align: right; padding-top: .25rem;
}
</style>
