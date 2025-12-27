import json
import os
from flask import Flask, render_template, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "fintech_founder_key_2025"

USER_DB = 'users.json'
LEDGER_DB = 'ledger.json'

# --- SAFETY SYSTEM: Prevents Crashes ---
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
        return {} # Return empty dict if file is corrupted

def save_db(filename, data):
    with open(filename, 'w') as f: json.dump(data, f, indent=4)

# --- ROUTES ---
@app.route('/')
def index():
    if 'username' in session: return redirect(url_for('dashboard'))
    return render_template('login.html')

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
    # Get user's data or empty list if new user
    user_txs = all_data.get(session['username'], [])
    
    # Calculate Math
    balance = sum(t['amount'] for t in user_txs)
    income = sum(t['amount'] for t in user_txs if t['amount'] > 0)
    expense = sum(t['amount'] for t in user_txs if t['amount'] < 0)

    return render_template('ledger.html', 
                           txs=user_txs[::-1], # Show newest first 
                           balance=balance, 
                           income=income, 
                           expense=expense, 
                           user=session['username'])

@app.route('/add', methods=['POST'])
def add_transaction():
    if 'username' not in session: return redirect(url_for('index'))
    
    try:
        amt = float(request.form.get('amount'))
        desc = request.form.get('description')
        t_type = request.form.get('type')
        
        final_amt = amt if t_type == 'income' else -amt
        
        all_data = load_db(LEDGER_DB)
        if session['username'] not in all_data: 
            all_data[session['username']] = []
            
        all_data[session['username']].append({
            "amount": final_amt,
            "description": desc,
            "type": t_type
        })
        save_db(LEDGER_DB, all_data)
    except:
        pass # Ignore errors for now
        
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)