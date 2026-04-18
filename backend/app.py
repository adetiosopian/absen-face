from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json, os, base64, uuid
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, 'data')
FACES_DIR  = os.path.join(DATA_DIR, 'faces')
STUDENTS_FILE  = os.path.join(DATA_DIR, 'students.json')
ATTENDANCE_FILE = os.path.join(DATA_DIR, 'attendance.json')

os.makedirs(FACES_DIR, exist_ok=True)
os.makedirs(DATA_DIR,  exist_ok=True)

# ── JSON Helpers ─────────────────────────────────────────
def read_json(path, default=None):
    if default is None:
        default = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Students ──────────────────────────────────────────────
@app.route('/api/students', methods=['GET'])
def get_students():
    return jsonify(read_json(STUDENTS_FILE))

@app.route('/api/students', methods=['POST'])
def add_student():
    data      = request.get_json(force=True)
    name      = (data.get('name') or '').strip()
    nim       = (data.get('nim')  or '').strip()
    descriptors = data.get('descriptors', []) # Sekarang menerima list
    photos      = data.get('photos', [])      # Sekarang menerima list foto

    if not name or not nim:
        return jsonify({'error': 'Nama dan NIM wajib diisi'}), 400

    students = read_json(STUDENTS_FILE)
    if any(s['nim'] == nim for s in students):
        return jsonify({'error': f'NIM {nim} sudah terdaftar'}), 409

    # Simpan hanya foto pertama sebagai primary thumbnail
    photo_url = None
    if photos:
        try:
            main_photo_b64 = photos[0]
            if ',' in main_photo_b64:
                main_photo_b64 = main_photo_b64.split(',', 1)[1]
            img_bytes = base64.b64decode(main_photo_b64)
            fname = f"{nim}_{uuid.uuid4().hex[:8]}.jpg"
            with open(os.path.join(FACES_DIR, fname), 'wb') as f:
                f.write(img_bytes)
            photo_url = f"/api/faces/{fname}"
        except Exception as e:
            print(f"[WARN] Photo save failed: {e}")

    student = {
        'id': uuid.uuid4().hex,
        'name': name,
        'nim': nim,
        'descriptors': descriptors, # Multiple descriptors stored here
        'photo_url': photo_url,
        'registered_at': datetime.now().isoformat()
    }
    students.append(student)
    write_json(STUDENTS_FILE, students)

    # Return without heavy descriptor payload
    safe = {k: v for k, v in student.items() if k != 'descriptor'}
    return jsonify({'message': 'Berhasil didaftarkan', 'student': safe}), 201

@app.route('/api/students/<nim>', methods=['DELETE'])
def delete_student(nim):
    students = read_json(STUDENTS_FILE)
    target   = next((s for s in students if s['nim'] == nim), None)
    if target and target.get('photo_url'):
        fname = target['photo_url'].split('/')[-1]
        try:
            os.remove(os.path.join(FACES_DIR, fname))
        except FileNotFoundError:
            pass
    students = [s for s in students if s['nim'] != nim]
    write_json(STUDENTS_FILE, students)
    return jsonify({'message': 'Mahasiswa dihapus'})

@app.route('/api/faces/<filename>')
def serve_face(filename):
    return send_from_directory(FACES_DIR, filename)

# ── Attendance ────────────────────────────────────────────
@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    att  = read_json(ATTENDANCE_FILE)
    return jsonify([a for a in att if a['date'] == date])

@app.route('/api/attendance', methods=['POST'])
def add_attendance():
    data  = request.get_json(force=True)
    nim   = (data.get('nim')  or '').strip()
    name  = (data.get('name') or '').strip()
    type_ = data.get('type', 'masuk')   # 'masuk' | 'pulang'
    status = data.get('status', 'hadir') # 'hadir' | 'ijin' | 'alfa'

    if not nim: return jsonify({'error': 'NIM wajib diisi'}), 400

    att   = read_json(ATTENDANCE_FILE)
    today = datetime.now().strftime('%Y-%m-%d')
    now   = datetime.now()

    # Cegah duplikasi untuk status yang sama di hari yang sama
    # Kecuali untuk 'masuk'/'pulang' yang merupakan bagian dari status 'hadir'
    if status == 'hadir':
        dup = next((a for a in att if a['nim'] == nim and a['date'] == today and a['type'] == type_), None)
        if dup: return jsonify({'error': f'Sudah absen {type_} hari ini'}), 409
    else:
        # Untuk Ijin/Alfa, hanya boleh sekali per hari
        dup = next((a for a in att if a['nim'] == nim and a['date'] == today), None)
        if dup: return jsonify({'error': f'Mahasiswa sudah memiliki status hari ini'}), 409

    record = {
        'id': uuid.uuid4().hex,
        'nim': nim,
        'name': name,
        'type': type_,
        'status': status,
        'timestamp': now.isoformat(),
        'date': today,
        'time': now.strftime('%H:%M:%S')
    }
    att.append(record)
    write_json(ATTENDANCE_FILE, att)
    return jsonify({'message': 'Berhasil dicatat', 'record': record}), 201

# ── Admin Stats ───────────────────────────────────────────
@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    students = read_json(STUDENTS_FILE)
    att      = read_json(ATTENDANCE_FILE)
    today    = datetime.now().strftime('%Y-%m-%d')
    
    today_att = [a for a in att if a['date'] == today]
    
    hadir = len(set(a['nim'] for a in today_att if a['status'] == 'hadir'))
    ijin  = len(set(a['nim'] for a in today_att if a['status'] == 'ijin'))
    alfa  = len(set(a['nim'] for a in today_att if a['status'] == 'alfa'))
    
    total = len(students)
    # Alfa otomatis = Total - (Hadir + Ijin + Alfa yang diinput manual)
    real_alfa = max(0, total - (hadir + ijin))

    return jsonify({
        'total': total,
        'hadir': hadir,
        'ijin': ijin,
        'alfa': real_alfa,
        'percentage': round((hadir / total * 100), 1) if total > 0 else 0
    })

@app.route('/api/attendance/<rec_id>', methods=['DELETE'])
def delete_record(rec_id):
    att = [a for a in read_json(ATTENDANCE_FILE) if a['id'] != rec_id]
    write_json(ATTENDANCE_FILE, att)
    return jsonify({'message': 'Record dihapus'})

@app.route('/api/attendance/clear', methods=['DELETE'])
def clear_attendance():
    write_json(ATTENDANCE_FILE, [])
    return jsonify({'message': 'Semua riwayat dihapus'})

# ── Stats ─────────────────────────────────────────────────
@app.route('/api/stats', methods=['GET'])
def get_stats():
    students = read_json(STUDENTS_FILE)
    att      = read_json(ATTENDANCE_FILE)
    today    = datetime.now().strftime('%Y-%m-%d')

    hadir_nims  = set(a['nim'] for a in att if a['date'] == today and a['type'] == 'masuk')
    pulang_nims = set(a['nim'] for a in att if a['date'] == today and a['type'] == 'pulang')

    week = []
    for i in range(6, -1, -1):
        d   = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        cnt = len(set(a['nim'] for a in att if a['date'] == d and a['type'] == 'masuk'))
        week.append({'date': d, 'label': d[5:], 'count': cnt})

    return jsonify({
        'total_students': len(students),
        'hadir_today':    len(hadir_nims),
        'pulang_today':   len(pulang_nims),
        'tidak_hadir':    max(0, len(students) - len(hadir_nims)),
        'week_data':      week
    })

if __name__ == '__main__':
    print("🚀 FaceAttend API  →  http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')
