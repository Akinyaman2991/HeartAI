from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for, send_from_directory
import pandas as pd
import pickle
import numpy as np
from fpdf import FPDF
import datetime
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'gizli_anahtar_degistirin_yoksa_hata_verir'

# VERİTABANI BAĞLANTISI 
def init_db():
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # 1. Kullanıcı Tablosu
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      name TEXT, email TEXT UNIQUE, password TEXT)''')
        
        # 2. Tahminler Tablosu (SIRALAMA KRİTİKTİR)
        c.execute('''CREATE TABLE IF NOT EXISTS predictions 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              user_id INTEGER,
              patient_name TEXT,
              date TEXT,
              age REAL,
              avg_glucose_level REAL,
              risk_score INTEGER,
              risk_label TEXT,
              bmi REAL,
              hypertension TEXT,
              heart_disease TEXT,
              id_no TEXT,
              birth_date TEXT,
              gender TEXT,
              phone TEXT,
              email TEXT,
              smoking_status TEXT,
              notes TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id))''')
                      
        # 3. Randevular Tablosu
        c.execute('''CREATE TABLE IF NOT EXISTS appointments 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id INTEGER,
                      patient_name TEXT,
                      appointment_date TEXT,
                      priority TEXT, 
                      FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # 4. Klinik İşlemler Tablosu (NOTLAR SÜTUNU 7. SIRADA)
        c.execute('''CREATE TABLE IF NOT EXISTS procedures 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id INTEGER,
                      patient_name TEXT,
                      procedure_name TEXT,
                      cost REAL,
                      status TEXT,
                      date TEXT,
                      notes TEXT, 
                      FOREIGN KEY(user_id) REFERENCES users(id))''')

        # 5. Tıbbi Dosya Arşivi Tablosu
        c.execute('''CREATE TABLE IF NOT EXISTS patient_files 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id INTEGER,
                      patient_name TEXT,
                      file_name TEXT,
                      file_type TEXT,
                      upload_date TEXT,
                      FOREIGN KEY(user_id) REFERENCES users(id))''')
        
        # 6. Diyet Planları Tablosu
        c.execute('''CREATE TABLE IF NOT EXISTS diet_plans 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      user_id INTEGER,
                      patient_name TEXT,
                      diet_content TEXT, 
                      create_date TEXT,
                      FOREIGN KEY(user_id) REFERENCES users(id))''')

        conn.commit()
        conn.close()
        print("Veritabanı notlar sütunu (7. index) dahil başarıyla güncellendi.")
    except Exception as e:
        print(f"DB Hatası: {e}")

# Uygulama başlarken veritabanını kurma
init_db()

# Model Yükleme
try:
    model = pickle.load(open('model/model.pkl', 'rb'))
    scaler = pickle.load(open('model/scaler.pkl', 'rb'))
    encoders = pickle.load(open('model/encoders.pkl', 'rb'))
    print("Model dosyaları başarıyla yüklendi.")
except Exception as e:
    print(f"MODEL YÜKLEME HATASI: {e}")
    print("Lütfen 'python model_egitimi_agresif.py' kodunu çalıştırıp model dosyalarını oluşturun!")

@app.route('/')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'Eksik bilgi!'})

    hashed_password = generate_password_hash(password)

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Kayıt başarılı! Giriş yapın.'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Bu E-Posta zaten kayıtlı!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            return jsonify({'success': True, 'message': 'Giriş başarılı!'})
        else:
            return jsonify({'success': False, 'message': 'Hatalı bilgiler!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f"Giriş hatası: {str(e)}"})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Kayıtlı hasta isimlerini çekiyoruz
    c.execute("SELECT DISTINCT patient_name FROM predictions WHERE user_id = ?", (session['user_id'],))
    all_names = [row[0] for row in c.fetchall()]
    conn.close()
    
    return render_template('dashboard.html', username=session.get('user_name'), registered_names=all_names)

# ROTASI DÜZELTİLDİ
@app.route('/patients')
def patients_page():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # GROUP BY patient_name ekleyerek isimlerin tekilleşmesini sağlıyoruz
    c.execute("""
        SELECT patient_name, MAX(date), age, risk_score, risk_label, id 
        FROM predictions 
        WHERE user_id = ? 
        GROUP BY patient_name
        ORDER BY id DESC
    """, (session['user_id'],))
    
    patients = c.fetchall()
    conn.close()
    return render_template('patients.html', patients=patients, username=session.get('user_name'))

@app.route('/all_procedures')
def all_procedures():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # GÜNCEL SORGU: Notları da (varsa) çekiyoruz
    c.execute("""SELECT patient_name, procedure_name, cost, date, status, id 
                 FROM procedures 
                 WHERE user_id = ? 
                 ORDER BY id DESC""", (session['user_id'],))
    all_procs = c.fetchall()
    
    c.execute("SELECT SUM(cost) FROM procedures WHERE user_id = ?", (session['user_id'],))
    total_income = c.fetchone()[0] or 0
    
    conn.close()
    return render_template('all_procedures.html', 
                           procedures=all_procs, 
                           total_income=total_income,
                           username=session.get('user_name'))

# --- YENİ İŞLEM SAYFASI (GÜNCEL ROTA) ---
@app.route('/create_procedure')
@app.route('/create_procedure/<patient_name>')
def create_procedure_page(patient_name=None):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # ÖNEMLİ: Daha önce kayıt olmuş TÜM hastaların isimlerini çekiyoruz
    # Böylece "Hasta Seçimi" kutusuna tıkladığında tüm liste açılır.
    c.execute("SELECT DISTINCT patient_name FROM predictions WHERE user_id = ?", (session['user_id'],))
    patient_list = [row[0] for row in c.fetchall()]
    conn.close()
    
    return render_template('create_procedure.html', 
                           patients=patient_list, 
                           selected_patient=patient_name, 
                           username=session.get('user_name'))

# ROTASI DÜZELTİLDİ VE PATIENT_NAME EKLENDİ
@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        # Verileri çek (patient_name eklendi)
        c.execute("SELECT date, patient_name, age, avg_glucose_level, risk_score, risk_label FROM predictions WHERE user_id = ? ORDER BY id DESC", (session['user_id'],))
        records = c.fetchall()
        conn.close()
        return render_template('history.html', records=records, username=session.get('user_name', 'Kullanıcı'))
    except Exception as e:
        return f"Geçmiş verileri çekilirken hata oluştu: {str(e)} <br> Lütfen database.db dosyasını silip tekrar deneyin."

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.json
        patient_name = data.get('patient_name', 'Bilinmeyen Hasta')

        # --- 1. KRİTİK KONTROL: HASTA KAYITLI MI? (BURAYA EKLENDİ) ---
        if 'user_id' in session:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            # Predictions tablosunda bu isme sahip bir kayıt var mı bakıyoruz
            c.execute("SELECT id FROM predictions WHERE user_id = ? AND patient_name = ?", 
                      (session['user_id'], patient_name))
            is_registered = c.fetchone()
            conn.close()

            if not is_registered:
                # Eğer kayıt bulunamazsa analizi durdur ve hata mesajı gönder
                return jsonify({
                    'success': False, 
                    'error': f"HATA: '{patient_name}' isminde bir hasta kaydı bulunamadı! Lütfen önce 'Yeni Hasta Kaydı' bölümünden hastayı sisteme tanıtın."
                })
        # --- KONTROL BİTTİ ---

        expected_order = ['gender', 'age', 'hypertension', 'heart_disease', 'ever_married', 
                          'work_type', 'Residence_type', 'avg_glucose_level', 'bmi', 'smoking_status']
        
        # Model tahmini için veriyi hazırla
        input_data = pd.DataFrame([data])
        input_model = input_data[expected_order].copy() 

        for col, le in encoders.items():
            try:
                if input_model[col].dtype == 'object':
                    input_model[col] = input_model[col].apply(lambda x: x if x in le.classes_ else le.classes_[0])
                    input_model[col] = le.transform(input_model[col])
            except:
                input_model[col] = 0

        input_model['bmi'] = input_model['bmi'].astype(float)
        input_model['age'] = input_model['age'].astype(float)
        input_model['avg_glucose_level'] = input_model['avg_glucose_level'].astype(float)
        
        input_scaled = scaler.transform(input_model)
        probability = model.predict_proba(input_scaled)[0][1]
        risk_score = int(probability * 100)
        
        risk_label = "YÜKSEK RİSK" if risk_score > 20 else ("Orta Risk" if risk_score > 10 else "Düşük Risk")

        # --- KALP YAŞI HESAPLAMA ---
        real_age = float(data['age'])
        heart_age = real_age
        if risk_score > 10: heart_age += 3
        if risk_score > 25: heart_age += 7
        if float(data['avg_glucose_level']) > 140: heart_age += 4
        if data['hypertension'] == "1": heart_age += 5
        
        projection = round(risk_score * 1.6, 1) 
        if projection > 100: projection = 100

        # --- VERİTABANINA GÜNCELLEME (Kayıtlı hastanın bilgilerini doldurur) ---
        if 'user_id' in session:
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            import datetime
            now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")

            # Mevcut kaydı bul ve güncelle
            c.execute("SELECT id FROM predictions WHERE user_id = ? AND patient_name = ? ORDER BY id DESC LIMIT 1", 
                      (session['user_id'], patient_name))
            existing_record = c.fetchone()

            if existing_record:
                c.execute("""UPDATE predictions SET 
                             date = ?, age = ?, avg_glucose_level = ?, 
                             risk_score = ?, risk_label = ?, bmi = ? 
                             WHERE id = ?""", 
                          (now, float(data['age']), float(data['avg_glucose_level']), 
                           risk_score, risk_label, float(data['bmi']), existing_record[0]))
                conn.commit()
            conn.close()

        # AI Tavsiyesi
        ai_advice = "Glikoz kontrolü ve kardiyak takip önerilir." if risk_score > 15 else "Düzenli egzersiz önerilir."

        return jsonify({
            'success': True, 
            'risk_score': risk_score, 
            'risk_label': risk_label,
            'heart_age': int(heart_age),
            'projection': projection,
            'ai_advice': ai_advice,
            'is_critical': True if risk_score > 20 else False
        })

    except Exception as e:
        print(f"Sistem Hatası: {str(e)}")
        return jsonify({'success': False, 'error': "Analiz sırasında bir hata oluştu!"})
@app.route('/appointments')
def appointments():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Randevuları tarihe göre sıralayarak çekiyoruz
    c.execute("""SELECT id, patient_name, appointment_date, priority 
                 FROM appointments 
                 WHERE user_id = ? 
                 ORDER BY appointment_date ASC""", (session['user_id'],))
    apps = c.fetchall()
    conn.close()
    return render_template('appointments.html', appointments=apps, username=session.get('user_name'))

@app.route('/add_appointment', methods=['POST'])
def add_appointment():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    name = request.form.get('patient_name')
    date = request.form.get('app_date') # Format: 2023-10-25T14:30
    priority = request.form.get('priority')
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("INSERT INTO appointments (user_id, patient_name, appointment_date, priority) VALUES (?, ?, ?, ?)",
              (session['user_id'], name, date, priority))
    conn.commit()
    conn.close()
    return redirect(url_for('appointments'))
    
    
    # --- YENİ: MONİTÖR SAYFASI ROTASI ---
@app.route('/monitor/<patient_name>')
def monitor(patient_name):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    return render_template('monitor.html', patient_name=patient_name, username=session.get('user_name'))

@app.route('/api/urgent_tasks')
def urgent_tasks():
    if 'user_id' not in session: return jsonify([])
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Son 24 saatte analiz edilen ve riski %20 üzeri olan hastaları getir
    c.execute("""SELECT patient_name, risk_score, risk_label, date 
                 FROM predictions 
                 WHERE user_id = ? AND risk_score > 20 
                 ORDER BY id DESC LIMIT 5""", (session['user_id'],))
    tasks = c.fetchall()
    conn.close()
    
    # JSON formatına dönüştür
    return jsonify([{
        "name": t[0],
        "score": t[1],
        "label": t[2],
        "time": t[3]
    } for t in tasks])

@app.route('/api/stats')
def get_stats():
    if 'user_id' not in session: return jsonify({})
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    
    
    # Toplam Analiz
    c.execute("SELECT COUNT(*) FROM predictions WHERE user_id = ?", (session['user_id'],))
    total = c.fetchone()[0]
    
    # Kritik (Yüksek Riskli) Sayısı
    c.execute("SELECT COUNT(*) FROM predictions WHERE user_id = ? AND risk_score > 20", (session['user_id'],))
    critical = c.fetchone()[0]
    
    # Ortalama Risk Skoru
    c.execute("SELECT AVG(risk_score) FROM predictions WHERE user_id = ?", (session['user_id'],))
    avg_risk = round(c.fetchone()[0] or 0, 1)

    # Bugünün randevu sayısını al
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM appointments WHERE user_id = ? AND appointment_date LIKE ?", (session['user_id'], today + '%'))
    today_apps = c.fetchone()[0]

    conn.close()
    return jsonify({
        "total": total,
        "critical": critical,
        "avg_risk": avg_risk,
        "today_apps": today_apps, # Bu satırı ekledik
        "success_rate": 98.4
    })

# KLİNİK İŞLEMLER SAYFASI (Opsiyonel patient_name parametresi ile)
@app.route('/procedures')
@app.route('/procedures/<patient_name>')
def procedures_page(patient_name=None):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # Geçmiş işlemleri listele
    c.execute("""SELECT patient_name, procedure_name, cost, status, date 
                 FROM procedures WHERE user_id = ? ORDER BY id DESC""", (session['user_id'],))
    proc_list = c.fetchall()
    conn.close()
    
    # selected_patient değişkeni ile HTML'e ismi gönderiyoruz
    return render_template('procedures.html', 
                           procedures=proc_list, 
                           selected_patient=patient_name, 
                           username=session.get('user_name'))

# YENİ İŞLEM KAYDETME
@app.route('/add_procedure', methods=['POST'])
def add_procedure():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    # Formdan gelen verileri alıyoruz
    name = request.form.get('patient_name')
    proc = request.form.get('procedure_name')
    cost = request.form.get('cost')
    notes = request.form.get('notes') # Ekstra notları da alalım
    
    # Bugünün tarihini oluşturuyoruz
    import datetime
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    try:
        # İşlem Arşivine (procedures tablosu) yeni kaydı ekle
        c.execute("""INSERT INTO procedures (user_id, patient_name, procedure_name, cost, status, date) 
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (session['user_id'], name, proc, cost, 'Tamamlandı', now))
        
        conn.commit()
        # Kayıt başarılıysa İşlem Arşivi sayfasına yönlendir
        return redirect(url_for('all_procedures'))
    except Exception as e:
        print(f"İşlem ekleme hatası: {e}")
        return "Bir hata oluştu", 500
    finally:
        conn.close()

@app.route('/patient_detail/<name>')
def patient_detail(name):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("""SELECT date, age, avg_glucose_level, risk_score, risk_label, bmi, hypertension, heart_disease 
                 FROM predictions 
                 WHERE user_id = ? AND patient_name = ? 
                 ORDER BY id ASC""", (session['user_id'], name))
    history = c.fetchall()
    conn.close()

    prescriptions = []
    
    # --- HATA ÇÖZÜMÜ: EĞER HASTA YENİYSE VE HİÇ ANALİZİ YOKSA ---
    if history:
        last_record = history[-1]
        age, glucose, risk, bmi = last_record[1], last_record[2], last_record[3], last_record[5]
        
        # Risk skoru 0 olan yeni hastalar için ağır ilaçlar önerme
        if risk > 20:
            prescriptions.append({"ilaç": "Aspirin (Düşük Doz)", "doz": "100mg 1x1", "neden": "Yüksek İnme Riski"})
        if glucose and float(glucose) > 140:
            prescriptions.append({"ilaç": "Metformin", "doz": "500mg 2x1", "neden": "Yüksek Kan Şekeri"})
        
        prescriptions.append({"ilaç": "Omega-3", "doz": "1000mg 1x1", "neden": "Genel Kalp Sağlığı Takviyesi"})
    else:
        # Hiç kayıt yoksa boş liste döndür veya genel bir not ekle
        prescriptions.append({"ilaç": "-", "doz": "-", "neden": "İlk analiz bekleniyor."})

    return render_template('patient_detail.html', patient_name=name, history=history, prescriptions=prescriptions, username=session.get('user_name'))



# --- YENİ: CANLI VERİ SİMÜLASYONU (API) ---
@app.route('/api/live_heart_data')
def live_heart_data():
    # Burada gerçek bir sensör varmış gibi rastgele nabız ve oksijen üretiyoruz
    import random
    data = {
        "bpm": random.randint(70, 85),
        "spo2": random.randint(95, 99),
        "temp": round(random.uniform(36.5, 37.2), 1)
    }
    return jsonify(data)

@app.route('/download_report', methods=['POST'])
def download_report():
    try:
        data = request.json
        pdf = FPDF()
        pdf.add_page()
        
        # Türkçe karakter sorunu olmaması için gereken kısım
        pdf.set_font("Arial", 'B', 20)
        pdf.cell(200, 10, txt="HealthGuard AI - Risk Raporu", ln=True, align='C')
        
        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        pdf.cell(200, 10, txt=f"Tarih: {datetime.datetime.now().strftime('%d-%m-%Y %H:%M')}", ln=True, align='R')
        
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 14)
        # PDF'te formdan gelen Hasta adının yazması düzeltildi
        patient_name = data.get('details', {}).get('patient_name', 'Bilinmeyen Hasta')
        pdf.cell(200, 10, txt=f"Hasta: {patient_name}", ln=True)
        
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        
        if 'details' in data:
            for key, value in data['details'].items():
                pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
        
        pdf.ln(20)
        pdf.set_font("Arial", 'B', 16)
        
        if "YÜKSEK" in data.get('result', ''):
            pdf.set_text_color(255, 0, 0)
        else:
            pdf.set_text_color(0, 128, 0)
            
        pdf.cell(200, 10, txt=f"SONUC: {data.get('result', 'Belirsiz')} (Skor: %{data.get('score', 0)})", ln=True, align='C')
        
        response = make_response(pdf.output(dest='S').encode('latin-1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=Risk_Raporu.pdf'
        return response
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    
    # --- 1. AYARLAR (app = Flask(__name__) satırının hemen altına yapıştır) ---
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Klasör yoksa otomatik oluşturur
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# --- 2. ROTALAR (Dosyanın en altına, diğer rotaların yanına yapıştır) ---

# --- DOSYA YÜKLEME ROTASI ---
@app.route('/upload_file/<patient_name>', methods=['POST']) # <--- Buranın HTML ile aynı olması şart
def upload_file(patient_name):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    if 'medical_file' not in request.files: return redirect(request.referrer)
    file = request.files['medical_file']
    file_type = request.form.get('file_type', 'Tahlil')
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + filename
        
        # Klasör yolunu garantiye alalım
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
        file.save(save_path)
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO patient_files (user_id, patient_name, file_name, file_type, upload_date) VALUES (?, ?, ?, ?, ?)",
                  (session['user_id'], patient_name, unique_name, file_type, datetime.now().strftime("%d.%m.%Y %H:%M")))
        conn.commit()
        conn.close()
    return redirect(request.referrer)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Yüklenen dosyaları tarayıcıda açmaya yarayan rota
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete_file/<int:file_id>')
def delete_file(file_id):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT file_name FROM patient_files WHERE id = ? AND user_id = ?", (file_id, session['user_id']))
    file_data = c.fetchone()
    
    if file_data:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file_data[0]))
        except: pass
        c.execute("DELETE FROM patient_files WHERE id = ? AND user_id = ?", (file_id, session['user_id']))
        conn.commit()
    conn.close()
    return redirect(request.referrer)



# --- TIBBİ DİYET SİSTEMİ (KESİN ÇÖZÜM) ---

@app.route('/diet_plan')
def diet_selection():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Tüm işlemleri en yeniden en eskiye doğru (ID DESC) çekiyoruz
    c.execute("""
        SELECT patient_name, date, age, risk_score, risk_label, id 
        FROM predictions 
        WHERE user_id = ? 
        ORDER BY id DESC
    """, (session['user_id'],))
    
    patients_list = c.fetchall()
    conn.close()
    
    # Terminalde kaç kayıt geldiğini kontrol et
    print(f"DEBUG: Toplam {len(patients_list)} işlem listeleniyor.") 
    
    return render_template('diet_selection.html', patients=patients_list)
# --- 2. HASTAYA ÖZEL DİYET SAYFASI ---
@app.route('/patient_diet/<int:patient_id>')
def patient_diet(patient_id):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT patient_name, avg_glucose_level, risk_score FROM predictions WHERE id = ?", (patient_id,))
    patient = c.fetchone()
    conn.close()

    if not patient: return redirect(url_for('diet_selection'))

    name, glucose, risk = patient[0], patient[1], (patient[2] or 0) # Risk None ise 0 yap

    # --- HATA ÇÖZÜMÜ: EĞER RİSK HENÜZ HESAPLANMADIYSA ---
    if risk == 0:
        special_title = "Genel Sağlıklı Yaşam ve Hazırlık Diyeti"
        note = "Henüz detaylı risk analizi yapılmadığı için genel kalp dostu beslenme önerilir. Analiz sonrası plan güncellenecektir."
        breakfast, dinner = "Haşlanmış yumurta, mevsim yeşillikleri", "Zeytinyağlı sebze yemeği, az yağlı yoğurt"
    elif glucose > 140:
        special_title = "Düşük Şeker (Diyabetik) Beslenme Protokolü"
        note = "Analiz sonucunda glikoz seviyeniz yüksek çıktığı için düşük karbonhidratlı bir plan hazırlanmıştır."
        breakfast, dinner = "Lor peynirli omlet, 2 tam ceviz", "Izgara tavuk, bol yeşil salata"
    elif risk > 20:
        special_title = "Yüksek Risk Grubu Kardiyovasküler Diyet"
        note = "Risk skorunuz %20 üzerinde olduğu için sodyum (tuz) kısıtlanmış ve Omega-3 artırılmıştır."
        breakfast, dinner = "Yulaf ezmesi, keten tohumu, meyve", "Fırın somon (tuzsuz), roka salatası"
    else:
        special_title = "Kalp Dostu Standart Akdeniz Diyeti"
        note = "Sağlık durumunuz stabil. Mevcut formu korumak için lifli beslenmeye devam edin."
        breakfast, dinner = "Tam buğday ekmeği, beyaz peynir, zeytin", "Zeytinyağlı sebze yemeği, yoğurt"

    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    diet_plan = {day: {"Sabah": breakfast, "Öğle": "Mevsim Salatası + Protein", "Akşam": dinner} for day in days}

    return render_template('diet_plan.html', patient_name=name, diet_plan=diet_plan, note=note, special_title=special_title)

@app.route('/waiting_room')
def waiting_room():
    if 'user_id' not in session: 
        return redirect(url_for('login_page'))
    
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row 
        c = conn.cursor()
        
        # Randevuları çek (Tablondaki sütun adı 'appointment_date' olduğu için düzelttim)
        c.execute("""SELECT patient_name, appointment_date 
                     FROM appointments 
                     WHERE user_id = ? 
                     ORDER BY appointment_date ASC LIMIT 6""", (session['user_id'],))
        appointments = c.fetchall()
        
        # Ekranda dönecek sağlık tavsiyeleri
        health_tips = [
            "Yapay zeka destekli analizimiz %98.4 doğrulukla çalışmaktadır.",
            "Günde 30 dakika yürüyüş kalp sağlığınızı korumaya yardımcı olur.",
            "Bol su içmek kan akışını düzenler ve kalbin yükünü hafifletir.",
            "Lütfen randevu saatinizden 5 dakika önce hazır bulununuz.",
            "Sağlıklı bir uyku, vücudun kendini onarması için en kritik evredir."
        ]
        
        conn.close()
        return render_template('waiting_room.html', appointments=appointments, tips=health_tips)
    except Exception as e:
        return f"Veritabanı hatası: {e}", 500
    
@app.route('/new_patient_registration', methods=['GET', 'POST'])
def new_patient_registration():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if request.method == 'POST':
        p_id = request.form.get('patient_id')
        p_name = request.form.get('patient_name')
        id_no = request.form.get('id_no')
        birth_date = request.form.get('birth_date')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        age = request.form.get('age') or 0
        glucose = request.form.get('avg_glucose_level') or 0
        bmi = request.form.get('bmi') or 0
        notes = request.form.get('notes')
        
        now = datetime.datetime.now()
        analiz_tarihi = now.strftime("%d.%m.%Y %H:%M") # Tablo için
        randevu_formati = now.strftime("%Y-%m-%dT%H:%M") # Bekleme salonu sıralaması için

        try:
            if p_id:
                # GÜNCELLEME MODU
                c.execute("""UPDATE predictions SET 
                             patient_name=?, id_no=?, birth_date=?, gender=?, phone=?, 
                             email=?, age=?, avg_glucose_level=?, bmi=?, notes=?, date=? 
                             WHERE id=? AND user_id=?""", 
                          (p_name, id_no, birth_date, gender, phone, email, age, glucose, bmi, notes, analiz_tarihi, p_id, session['user_id']))
            else:
                # 1. ANALİZ TABLOSUNA KAYIT (İstatistikler ve Arşiv için)
                c.execute("""INSERT INTO predictions 
                             (user_id, patient_name, id_no, birth_date, gender, phone, email, age, avg_glucose_level, bmi, notes, date, risk_label, risk_score) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
                          (session['user_id'], p_name, id_no, birth_date, gender, phone, email, age, glucose, bmi, notes, analiz_tarihi, 'Analiz Bekliyor', 0))
                
                # 2. BEKLEME SALONU TABLOSUNA KAYIT (TV Ekranına düşmesi için KRİTİK ADIM)
                c.execute("""INSERT INTO appointments (user_id, patient_name, appointment_date, priority) 
                             VALUES (?, ?, ?, ?)""",
                          (session['user_id'], p_name, randevu_formati, 'Normal'))
            
            conn.commit()
        except Exception as e:
            print(f"Kayıt Hatası: {e}")
            conn.rollback()
        finally:
            conn.close()
            
        return redirect(url_for('new_patient_registration'))

    # Sayfa yükleme kodları (SELECT sorgusu) buranın altında devam eder...

    # Tabloyu doldurmak için verileri çek (Sıralama HTML'deki p[index] ile uyumlu olmalı)
    c.execute("""SELECT id, patient_name, date, age, avg_glucose_level, bmi, risk_label, 
                        id_no, birth_date, gender, phone, email, smoking_status, notes 
                 FROM predictions WHERE user_id = ? ORDER BY id DESC LIMIT 10""", (session['user_id'],))
    recent_patients = c.fetchall()
    conn.close()
    
    return render_template('new_patient.html', recent_patients=recent_patients, username=session.get('user_name'))
    
   # DOSYANIN EN SON SATIRLARI BUNLAR OLMALI
if __name__ == '__main__':
    app.run(debug=True)