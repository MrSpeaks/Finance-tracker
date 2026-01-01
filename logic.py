import json, os
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "any_long_random_string_here_12345"

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
@app.route('/auth', methods=['POST'])
def auth():
    # Get values from the form
    action = request.form.get('action')
    user = request.form.get('username')
    pwd = request.form.get('password')
    
    db = load_db(USER_DB)

    if action == 'signup':
        if user in db:
            return "User already exists! <a href='/'>Try Login</a>"
        # Hash the password and save
        db[user] = generate_password_hash(pwd)
        save_db(USER_DB, db)
        session['username'] = user
        session['currency'] = 'USD' # Default currency for new users
        return redirect(url_for('dashboard'))

    elif action == 'login':
        # 1. Check if user exists
        if user not in db:
            return "User not found! <a href='/'>Sign up here</a>"
        
        # 2. Check if password is correct
        if check_password_hash(db[user], pwd):
            session['username'] = user
            # Keep their currency preference if it exists, otherwise USD
            if 'currency' not in session:
                session['currency'] = 'USD'
            return redirect(url_for('dashboard'))
        else:
            return "Wrong password! <a href='/'>Try again</a>"
    
    return "Unknown Error. <a href='/'>Go back</a>"

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
    try:
        # 1. Get data safely
        raw_amount = request.form.get('amount')
        desc = request.form.get('description', 'No Description')
        t_type = request.form.get('type')
        
        if not raw_amount:
            return "Error: Please enter an amount! <a href='/dashboard'>Go back</a>"
            
        amt = float(raw_amount)
        mode = session.get('currency', 'USD')
        
        # 2. Handle Conversion
        val = (amt / 83.0) if mode == 'INR' else amt
        val = val if t_type == 'income' else -val

        # 3. Load DB with Error Handling
        db = load_db(LEDGER_DB)
        user = session.get('username')
        
        if not user:
            return redirect(url_for('index'))

        if user not in db: 
            db[user] = []
            
        # 4. Create Entry
        db[user].append({
            "amount": val, 
            "description": desc, 
            "type": t_type,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%I:%M %p")
        })
        
        # 5. Save with confirmation
        save_db(LEDGER_DB, db)
        return redirect(url_for('dashboard'))

    except Exception as e:
        # This will show the real error on your screen instead of 'Internal Server Error'
        return f"Logic Error: {str(e)}. <a href='/dashboard'>Go back</a>"

def load_db(filename):
    # If file doesn't exist, create it with empty braces
    if not os.path.exists(filename): 
        with open(filename, 'w') as f: 
            json.dump({}, f)
        return {}
    
    # If file exists but is empty, return empty dict and fix the file
    if os.stat(filename).st_size == 0:
        with open(filename, 'w') as f: 
            json.dump({}, f)
        return {}

    try:
        with open(filename, 'r') as f: 
            return json.load(f)
    except json.JSONDecodeError:
        # If the file is corrupted/invalid, reset it
        with open(filename, 'w') as f: 
            json.dump({}, f)
        return {}


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