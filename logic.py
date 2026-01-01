import json, os
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "fintech_v2_ultra_secret_key"

USER_DB = 'users.json'
LEDGER_DB = 'ledger.json'

# --- DATABASE HELPERS ---
def load_db(filename):
    if not os.path.exists(filename): 
        with open(filename, 'w') as f: json.dump({}, f)
    with open(filename, 'r') as f: return json.load(f)

def save_db(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- ROUTES ---
@app.route('/')
def index():
    if 'username' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def auth():
    action, user, pwd = request.form.get('action'), request.form.get('username'), request.form.get('password')
    db = load_db(USER_DB)
    if action == 'signup':
        if user in db: return "User exists!"
        db[user] = generate_password_hash(pwd)
        save_db(USER_DB, db)
        session['username'] = user
    else:
        if user in db and check_password_hash(db[user], pwd): session['username'] = user
        else: return "Invalid Login! <a href='/'>Try again</a>"
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('index'))
    user = session['username']
    data = load_db(LEDGER_DB).get(user, [])
    
    # Currency Logic
    mode = session.get('currency', 'USD')
    rate, sym = (83.0, '₹') if mode == 'INR' else (1.0, '$')

    # Date Filtering
    today = datetime.now().strftime("%Y-%m-%d")
    today_txs = [t for t in data if t.get('date') == today]
    
    # Calculations (Store everything in USD base)
    bal = sum(t['amount'] for t in data)
    inc = sum(t['amount'] for t in data if t['amount'] > 0)
    exp = sum(t['amount'] for t in data if t['amount'] < 0)

    return render_template('dashboard.html', today_txs=today_txs[::-1], 
                           balance=bal*rate, income=inc*rate, expense=exp*rate,
                           symbol=sym, currency=mode)

@app.route('/add', methods=['POST'])
def add():
    amt, desc, t_type = float(request.form.get('amount')), request.form.get('description'), request.form.get('type')
    mode = session.get('currency', 'USD')
    
    # CONVERSION: If adding in INR mode, divide by 83 to store as USD
    val = (amt / 83.0) if mode == 'INR' else amt
    val = val if t_type == 'income' else -val

    db = load_db(LEDGER_DB)
    if session['username'] not in db: db[session['username']] = []
    db[session['username']].append({
        "amount": val, "description": desc, "type": t_type,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%I:%M %p")
    })
    save_db(LEDGER_DB, db)
    return redirect(url_for('dashboard'))

@app.route('/toggle_currency')
def toggle():
    session['currency'] = 'INR' if session.get('currency', 'USD') == 'USD' else 'USD'
    return redirect(url_for('dashboard'))

@app.route('/history')
def history():
    if 'username' not in session: return redirect(url_for('index'))
    data = load_db(LEDGER_DB).get(session['username'], [])
    return render_template('history.html', txs=data[::-1])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)