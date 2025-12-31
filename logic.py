import json
import os
from datetime import datetime
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "fintech_v2_secret_key"

USER_DB = 'users.json'
LEDGER_DB = 'ledger.json'

# --- HELPERS ---
def init_db():
    if not os.path.exists(USER_DB):
        with open(USER_DB, 'w') as f: json.dump({}, f)
    if not os.path.exists(LEDGER_DB):
        with open(LEDGER_DB, 'w') as f: json.dump({}, f)

def load_db(filename):
    init_db()
    try:
        with open(filename, 'r') as f: return json.load(f)
    except:
        return {}

def save_db(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- ROUTES ---
@app.route('/')
def index():
    if 'username' in session: return redirect(url_for('dashboard'))
    return render_template('login.html') # Use the same login as before

@app.route('/auth', methods=['POST'])
def auth():
    action = request.form.get('action')
    username = request.form.get('username')
    password = request.form.get('password')
    users = load_db(USER_DB)

    if action == 'signup':
        if username in users: return "User already exists!"
        users[username] = generate_password_hash(password)
        save_db(USER_DB, users)
        session['username'] = username
        return redirect(url_for('dashboard'))
    
    elif action == 'login':
        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        return "Wrong username or password! <a href='/'>Try again</a>"

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect(url_for('index'))
    
    all_data = load_db(LEDGER_DB)
    user_txs = all_data.get(session['username'], [])
    
    # Get Current Date (YYYY-MM-DD)
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Filter Data
    today_txs = []
    history_txs = []
    
    for tx in user_txs:
        # tx['date'] will look like '2023-10-27'
        if tx.get('date') == today_str:
            today_txs.append(tx)
        else:
            history_txs.append(tx)
            
    # Calculate Totals
    balance = sum(t['amount'] for t in user_txs)
    income = sum(t['amount'] for t in user_txs if t['amount'] > 0)
    expense = sum(t['amount'] for t in user_txs if t['amount'] < 0)

    # Get Currency Preference (Default to USD)
    currency = session.get('currency', 'USD')
    rate = 83 if currency == 'INR' else 1 # Simple conversion rate
    symbol = '₹' if currency == 'INR' else '$'

    return render_template('dashboard.html', 
                           today_txs=today_txs[::-1], 
                           balance=balance * rate, 
                           income=income * rate, 
                           expense=expense * rate,
                           user=session['username'],
                           symbol=symbol,
                           currency=currency)

@app.route('/add', methods=['POST'])


@app.route('/toggle_currency')
def toggle_currency():
    current = session.get('currency', 'USD')
    session['currency'] = 'INR' if current == 'USD' else 'USD'
    return redirect(url_for('dashboard'))

@app.route('/history')
def history():
    if 'username' not in session: return redirect(url_for('index'))
    all_data = load_db(LEDGER_DB)
    user_txs = all_data.get(session['username'], [])
    
    # Sort by newest first
    return render_template('history.html', txs=user_txs[::-1])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/add', methods=['POST'])
def add_transaction():
    if 'username' not in session: return redirect(url_for('index'))
    
    amt = float(request.form.get('amount'))
    desc = request.form.get('description')
    t_type = request.form.get('type')
    entry_currency = request.form.get('entry_currency') # New field from form

    # LOGIC: Convert input to USD for storage (Base Currency)
    # We store everything in one base currency to keep the total balance accurate
    if entry_currency == 'INR':
        stored_amt = amt / 83.0 # Convert to USD base
    else:
        stored_amt = amt

    final_amt = stored_amt if t_type == 'income' else -stored_amt
    
    now = datetime.now()
    new_tx = {
        "amount": final_amt,
        "description": desc,
        "type": t_type,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%I:%M %p"),
        "original_currency": entry_currency # Keep track of what they typed
    }

    all_data = load_db(LEDGER_DB)
    if session['username'] not in all_data: 
        all_data[session['username']] = []
        
    all_data[session['username']].append(new_tx)
    save_db(LEDGER_DB, all_data)
        
    return redirect(url_for('dashboard'))