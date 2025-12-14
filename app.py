import json
import sqlite3
import functools
import random
import os   # Untuk operasi sistem file
from flask import Flask, render_template, request, redirect, url_for, g, session, flash
from web3 import Web3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # Untuk mengamankan nama file

app = Flask(__name__)
app.secret_key = 'kunci_baru_biar_logout_semua_123'

# --- KONFIGURASI UPLOAD ---
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Buat folder uploads otomatis jika belum ada
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 1. KONEKSI BLOCKCHAIN ---
ganache_url = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(ganache_url))

if not web3.is_connected():
    print("⚠️ WARNING: Ganache tidak terhubung")
else:
    print("✅ Ganache terhubung")


def load_contract():
    try:
        with open('build/contracts/BookDonation.json') as f:
            contract_json = json.load(f)
        contract_abi = contract_json['abi']
        network_ids = list(contract_json['networks'].keys())
        if len(network_ids) > 0:
            latest_id = network_ids[-1]
            contract_address = contract_json['networks'][latest_id]['address']
            return web3.eth.contract(address=contract_address, abi=contract_abi)
        else:
            return None
    except:
        return None

contract = load_contract()

if contract is None:
    print("⚠️ WARNING: Smart contract belum ter-load")
else:
    print("✅ Smart contract siap digunakan")


# --- 2. DATABASE SETUP ---
DATABASE = 'debooks.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        
        # 1. Tabel Users
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL, 
            wallet_address TEXT
        )''')
        
        # 2. Tabel Campaigns (LENGKAP: Ada creator_bio & instagram_link)
        db.execute('''CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blockchain_id INTEGER,
            creator_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            creator_bio TEXT,
            instagram_link TEXT,
            category TEXT,
            location TEXT,
            deadline TEXT,
            image_filename TEXT, 
            target_amount REAL,
            status TEXT DEFAULT 'Active'
        )''')
        
        # 3. Tabel Donations (Donasi Langsung)
        db.execute('''CREATE TABLE IF NOT EXISTS donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            donor_id INTEGER,
            donor_name TEXT,
            donor_email TEXT,
            donor_phone TEXT,
            book_title TEXT,
            book_qty INTEGER,
            book_details TEXT,
            shipping_status TEXT DEFAULT 'Pending'
        )''')
        
        # 4. Tabel Pledges (Janji Donasi)
        db.execute('''CREATE TABLE IF NOT EXISTS pledges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            donor_id INTEGER,
            donor_name TEXT,
            donor_email TEXT,
            donor_phone TEXT,
            book_title TEXT,
            book_qty INTEGER,
            shipping_date TEXT,
            shipping_method TEXT,
            book_condition TEXT,
            estimated_weight REAL,
            status TEXT DEFAULT 'Committed'
        )''')
        
        # Admin Default
        check = db.execute("SELECT * FROM users WHERE username='admin'").fetchone()
        if not check:
            pw_hash = generate_password_hash('admin123')
            wallet_address = "0xe6313e6aAf3ac43F951bE89EeF70FBA42f201Be9"
            if web3.is_connected():
                acct = web3.eth.account.create()
                wallet_address = "0xe6313e6aAf3ac43F951bE89EeF70FBA42f201Be9"

                
            db.execute("INSERT INTO users (username, password, role, wallet_address) VALUES (?, ?, ?, ?)",
                       ('admin', pw_hash, 'admin', wallet_address))
            db.commit()

# --- 3. DECORATORS ---
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session or session['role'] != required_role:
                flash('Akses Ditolak')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- 4. ROUTES PUBLIC & AUTH ---

@app.route('/')
def index():
    db = get_db()
    campaigns = db.execute("SELECT * FROM campaigns WHERE status='Active' ORDER BY id DESC").fetchall()
    return render_template('index.html', campaigns=campaigns)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        wallet = request.form['wallet_address']
        
        db = get_db()
        
        user = db.execute(
    "SELECT * FROM users WHERE username = ? AND wallet_address = ?",
    (username, wallet)
).fetchone()

        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']
            session['wallet'] = user['wallet_address']
            
            if user['role'] == 'admin': return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'kreator': return redirect(url_for('kreator_dashboard'))
            else: return redirect(url_for('donatur_dashboard'))
        else:
            flash('Username atau Password salah.')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        wallet = request.form['wallet_address']   # ⬅️ SATU-SATUNYA PERUBAHAN

        db = get_db()
        error = None

        if not username:
            error = 'Username wajib diisi.'
        elif not password:
            error = 'Password wajib diisi.'
        elif not web3.is_address(wallet):
            error = 'Wallet address tidak valid.'
        elif db.execute(
            'SELECT id FROM users WHERE username = ?',
            (username,)
        ).fetchone() is not None:
            error = f"Username '{username}' sudah dipakai."

        if error is None:
            hashed_pw = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (username, password, role, wallet_address) VALUES (?, ?, ?, ?)",
                (username, hashed_pw, role, wallet)
            )
            db.commit()
            flash(f'Registrasi berhasil! Wallet: {wallet[:6]}...')
            return redirect(url_for('login'))

        flash(error)

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- 5. ROUTES DONATUR ---

@app.route('/donatur/dashboard')
@login_required
@role_required('donatur')
def donatur_dashboard():
    db = get_db()
    campaigns = db.execute("SELECT * FROM campaigns WHERE status='Active' ORDER BY id DESC").fetchall()
    return render_template('donatur_dashboard.html', campaigns=campaigns)

# >>> ROUTE BARU: DETAIL KAMPANYE DONATUR (Lihat Profil Dulu) <<<
@app.route('/donatur/campaign/<int:campaign_id>')
@login_required
@role_required('donatur')
def donatur_campaign_detail(campaign_id):
    db = get_db()
    campaign = db.execute('''
        SELECT c.*, u.username as creator_name 
        FROM campaigns c JOIN users u ON c.creator_id = u.id 
        WHERE c.id = ?
    ''', (campaign_id,)).fetchone()
    
    return render_template('donatur_campaign_detail.html', campaign=campaign)

@app.route('/donatur/donate/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
@role_required('donatur')
def donatur_form(campaign_id):
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        title = request.form['book_title']
        qty = request.form['book_qty']
        
        book_summary = f"{title} (Qty: {qty})"
        amount_eth = float(request.form.get('amount', 0.001))
        amount_wei = web3.to_wei(amount_eth, 'ether')
        
        try:
            tx_hash = contract.functions.donate(campaign_id, book_summary).transact({
                'from': session['wallet'],
                'value': amount_wei
            })

            web3.eth.wait_for_transaction_receipt(tx_hash)

            
            db.execute('''INSERT INTO donations 
                (campaign_id, donor_id, donor_name, donor_email, donor_phone, book_title, book_qty, book_details) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (campaign_id, session['user_id'], name, email, phone, title, qty, book_summary))
            db.commit()
            
            flash('Donasi Langsung Berhasil! Tercatat di Blockchain.')
            return redirect(url_for('donatur_status'))
            
        except Exception as e:
            flash(f'Error Blockchain: {str(e)}')

    campaign = db.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    return render_template('donatur_form.html', campaign=campaign)

@app.route('/donatur/pledge/<int:campaign_id>', methods=['GET', 'POST'])
@login_required
@role_required('donatur')
def donatur_pledge(campaign_id):
    db = get_db()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        book_title = request.form['book_title']
        book_qty = request.form['book_qty']
        
        shipping_date = request.form['shipping_date']
        method = request.form['method']
        condition = request.form['condition']
        weight = request.form['weight']
        
        db.execute('''INSERT INTO pledges 
            (campaign_id, donor_id, donor_name, donor_email, donor_phone, book_title, book_qty, shipping_date, shipping_method, book_condition, estimated_weight) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (campaign_id, session['user_id'], name, email, phone, book_title, book_qty, shipping_date, method, condition, weight))
        db.commit()
        
        flash('Janji Donasi Berhasil Disimpan! Silakan kirim buku Anda sesuai jadwal.')
        return redirect(url_for('donatur_status'))

    campaign = db.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    return render_template('donatur_pledge.html', campaign=campaign)

@app.route('/donatur/status')
@login_required
@role_required('donatur')
def donatur_status():
    db = get_db()
    
    donations = db.execute('''
        SELECT d.*, c.title as campaign_title, 'Direct' as type 
        FROM donations d JOIN campaigns c ON d.campaign_id = c.id
        WHERE d.donor_id = ? ORDER BY d.id DESC
    ''', (session['user_id'],)).fetchall()
    
    pledges = db.execute('''
        SELECT p.*, c.title as campaign_title, 'Pledge' as type
        FROM pledges p JOIN campaigns c ON p.campaign_id = c.id
        WHERE p.donor_id = ? ORDER BY p.id DESC
    ''', (session['user_id'],)).fetchall()
    
    return render_template('donatur_status.html', donations=donations, pledges=pledges)

# --- 6. ROUTES KREATOR ---

@app.route('/kreator/dashboard')
@login_required
@role_required('kreator')
def kreator_dashboard():
    db = get_db()
    campaigns = db.execute("SELECT * FROM campaigns WHERE creator_id=?", (session['user_id'],)).fetchall()
    return render_template('kreator_dashboard.html', campaigns=campaigns)

@app.route('/kreator/create', methods=['GET', 'POST'])
@login_required
@role_required('kreator')
def kreator_create():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        location = request.form['location']
        deadline = request.form['deadline']
        desc = request.form['desc']
        target = float(request.form['target'])
        
        # MENYIMPAN BIO & INSTAGRAM (FITUR BARU)
        creator_bio = request.form['creator_bio']
        instagram_link = request.form['instagram_link']

        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filename = filename
        
        try:
            target_wei = web3.to_wei(target, 'ether')
            tx_hash = contract.functions.createCampaign(target_wei).transact({
                'from': session['wallet']
            })
            web3.eth.wait_for_transaction_receipt(tx_hash)
            
            blockchain_id = contract.functions.campaignCount().call()
            
            db = get_db()
            db.execute('''INSERT INTO campaigns 
                (blockchain_id, creator_id, title, description, creator_bio, instagram_link, category, location, deadline, image_filename, target_amount, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (blockchain_id, session['user_id'], title, desc, creator_bio, instagram_link, category, location, deadline, image_filename, target, 'Pending'))
            db.commit()
            
            flash('Kampanye Berhasil Dibuat! Menunggu persetujuan Admin.')
            return redirect(url_for('kreator_dashboard'))
            
        except Exception as e:
            flash(f"Gagal deploy ke Blockchain: {e}")
            
    return render_template('kreator_create.html')

@app.route('/kreator/campaign/<int:campaign_id>')
@login_required
@role_required('kreator')
def kreator_campaign_detail(campaign_id):
    db = get_db()
    
    campaign = db.execute('SELECT * FROM campaigns WHERE id = ? AND creator_id = ?', 
                          (campaign_id, session['user_id'])).fetchone()
    
    if not campaign:
        flash('Kampanye tidak ditemukan atau Anda tidak memiliki akses.')
        return redirect(url_for('kreator_dashboard'))

    donations = db.execute('SELECT * FROM donations WHERE campaign_id = ? ORDER BY id DESC', (campaign_id,)).fetchall()
    pledges = db.execute('SELECT * FROM pledges WHERE campaign_id = ? ORDER BY id DESC', (campaign_id,)).fetchall()
    
    return render_template('kreator_campaign_detail.html', campaign=campaign, donations=donations, pledges=pledges)

# --- 7. ROUTES ADMIN ---

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_db()

    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_campaigns = db.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]

    pending_campaigns = db.execute(
        "SELECT COUNT(*) FROM campaigns WHERE status = 'Pending'"
    ).fetchone()[0]

    return render_template(
        'admin_dashboard.html',
        total_donatur=total_users,
        total_campaigns=total_campaigns,
        pending_campaigns=pending_campaigns
    )

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    db = get_db()
    users = db.execute("SELECT id, username, role, wallet_address FROM users ORDER BY id DESC").fetchall()
    return render_template('admin_users.html', users=users)

@app.route('/admin/campaigns')
@login_required
@role_required('admin')
def admin_campaigns():
    db = get_db()
    campaigns = db.execute('''
        SELECT c.*, u.username as creator_name 
        FROM campaigns c 
        JOIN users u ON c.creator_id = u.id 
        ORDER BY c.id DESC
    ''').fetchall()
    return render_template('admin_campaigns.html', campaigns=campaigns)

@app.route('/admin/campaign/status/<int:campaign_id>/<action>')
@login_required
@role_required('admin')
def admin_campaign_status(campaign_id, action):
    db = get_db()
    new_status = 'Pending'
    
    if action == 'approve':
        new_status = 'Active'
        msg = 'Kampanye disetujui dan sekarang Aktif!'
    elif action == 'reject':
        new_status = 'Rejected'
        msg = 'Kampanye ditolak.'
    else:
        return redirect(url_for('admin_campaigns'))
        
    db.execute("UPDATE campaigns SET status = ? WHERE id = ?", (new_status, campaign_id))
    db.commit()
    
    flash(msg)
    return redirect(url_for('admin_campaigns'))

# >>> ADMIN DETAIL KAMPANYE (LOGISTIK) <<<

@app.route('/admin/campaign/<int:campaign_id>')
@login_required
@role_required('admin')
def admin_campaign_detail(campaign_id):
    db = get_db()
    campaign = db.execute('''
        SELECT c.*, u.username as creator_name, u.wallet_address 
        FROM campaigns c JOIN users u ON c.creator_id = u.id 
        WHERE c.id = ?
    ''', (campaign_id,)).fetchone()
    
    donations = db.execute('''
        SELECT * FROM donations WHERE campaign_id = ? ORDER BY id DESC
    ''', (campaign_id,)).fetchall()
    
    pledges = db.execute('''
        SELECT * FROM pledges WHERE campaign_id = ? ORDER BY id DESC
    ''', (campaign_id,)).fetchall()
    
    return render_template('admin_campaign_detail.html', campaign=campaign, donations=donations, pledges=pledges)

@app.route('/admin/logistics/update/<string:type>/<int:id>/<string:status>')
@login_required
@role_required('admin')
def update_logistics(type, id, status):
    db = get_db()
    
    if type == 'donation':
        db.execute("UPDATE donations SET shipping_status = ? WHERE id = ?", (status, id))
        camp_id = db.execute("SELECT campaign_id FROM donations WHERE id=?", (id,)).fetchone()[0]
    elif type == 'pledge':
        db.execute("UPDATE pledges SET status = ? WHERE id = ?", (status, id))
        camp_id = db.execute("SELECT campaign_id FROM pledges WHERE id=?", (id,)).fetchone()[0]
        
    db.commit()
    flash(f'Status logistik berhasil diperbarui menjadi: {status}')
    
    return redirect(url_for('admin_campaign_detail', campaign_id=camp_id))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)