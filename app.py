import os, shutil, bcrypt
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import sys

# שאר ה-imports שלך...
from flask import Flask, ...

app = Flask(__name__)
app.secret_key = 'DA_PRIME_STUDIOS_17215' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///da_prime.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
db = SQLAlchemy(app)

# --- מודלים ---
class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100)); genre = db.Column(db.String(50))
    price = db.Column(db.String(50)); description = db.Column(db.Text)
    audio_path = db.Column(db.String(200)); image_path = db.Column(db.String(200))
    is_free = db.Column(db.Boolean, default=False)

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128))

class SiteSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), default="0500000000")
    whatsapp = db.Column(db.String(20), default="972500000000")
    watermark_file = db.Column(db.String(100))
    watermark_volume = db.Column(db.Integer, default=-20)

# --- לוגיקת אודיו ---
def process_audio(input_path, settings):
    playback = AudioSegment.from_file(input_path)
    if settings and settings.watermark_file:
        wm_path = os.path.join(app.config['UPLOAD_FOLDER'], settings.watermark_file)
        if os.path.exists(wm_path):
            watermark = AudioSegment.from_file(wm_path) + settings.watermark_volume
            playback = playback.overlay(watermark, loop=True)
    
    filename = "marked_" + os.path.basename(input_path)
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    playback.export(output_path, format="mp3", bitrate="128k")
    return filename

# --- נתיבים ---
@app.route('/')
def index():
    tracks = Track.query.all()
    genres = [g[0] for g in db.session.query(Track.genre).distinct().all() if g[0]]
    settings = SiteSettings.query.first() or SiteSettings()
    return render_template('index.html', tracks=tracks, settings=settings, genres=genres)

@app.route('/admin_login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].upper()
        password = request.form['password']
        admin = AdminUser.query.filter_by(email=email).first()
        if admin and bcrypt.checkpw(password.encode('utf-8'), admin.password_hash):
            session['user'] = email
            return redirect(url_for('admin_panel'))
        flash('פרטי התחברות שגויים')
    return render_template('login.html')

@app.route('/admin')
def admin_panel():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template('admin.html', tracks=Track.query.all(), 
                           admins=AdminUser.query.all(), settings=SiteSettings.query.first())

@app.route('/admin/upload', methods=['POST'])
def upload():
    if 'user' not in session: return "Access Denied", 403
    settings = SiteSettings.query.first()
    audio = request.files['audio']
    image = request.files['image']
    a_name = secure_filename(audio.filename)
    i_name = secure_filename(image.filename)
    t_path = os.path.join(app.config['UPLOAD_FOLDER'], a_name)
    audio.save(t_path)
    image.save(os.path.join(app.config['UPLOAD_FOLDER'], i_name))
    
    final_audio = process_audio(t_path, settings)
    db.session.add(Track(title=request.form['title'], genre=request.form['genre'], 
                         price=request.form['price'], description=request.form['desc'],
                         audio_path=final_audio, image_path=i_name))
    db.session.commit()
    os.remove(t_path)
    return redirect(url_for('admin_panel'))

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    if 'user' not in session: return "Access Denied", 403
    s = SiteSettings.query.first() or SiteSettings()
    s.phone = request.form['phone']; s.whatsapp = request.form['whatsapp']
    s.watermark_volume = int(request.form['wm_vol'])
    if 'wm_file' in request.files and request.files['wm_file'].filename:
        f = request.files['wm_file']
        name = secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], name))
        s.watermark_file = name
    db.session.add(s); db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_admin', methods=['POST'])
def add_admin():
    if 'user' not in session: return "Access Denied", 403
    email = request.form['email'].upper()
    hp = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
    db.session.add(AdminUser(email=email, password_hash=hp))
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/change_password', methods=['POST'])
def change_pass():
    if 'user' not in session: return "Access Denied", 403
    admin = AdminUser.query.filter_by(email=session['user']).first()
    admin.password_hash = bcrypt.hashpw(request.form['new_pass'].encode('utf-8'), bcrypt.gensalt())
    db.session.commit()
    flash("סיסמה שונתה בהצלחה")
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<int:id>')
def delete(id):
    if 'user' not in session: return "Access Denied", 403
    db.session.delete(Track.query.get(id)); db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.pop('user', None); return redirect(url_for('index'))

# --- אלו השורות החדשות שאתה מעתיק ---
if not os.path.exists(app.config['UPLOAD_FOLDER']): 
    os.makedirs(app.config['UPLOAD_FOLDER'])

with app.app_context():
    db.create_all()
    if not AdminUser.query.filter_by(email='DAVIDAZRAN11@GMAIL.COM').first():
        hp = bcrypt.hashpw('AAA17215'.encode('utf-8'), bcrypt.gensalt())
        db.session.add(AdminUser(email='DAVIDAZRAN11@GMAIL.COM', password_hash=hp))
        db.session.commit()

if __name__ == '__main__':
    app.run()