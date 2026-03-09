from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # Replace with a strong random key in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Float, default=5000.0) # Default balance
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(50), nullable=False) # e.g., 'Electricity Bill', 'Recharge'
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Success')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

# Routes

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required!', 'error')
            return redirect(url_for('index'))

        if action == 'signup':
            user = User.query.filter_by(username=username).first()
            if user:
                flash('Username already exists!', 'error')
                return redirect(url_for('index'))
            
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('index'))

        elif action == 'login':
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password!', 'error')
                return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = db.session.get(User, session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/paybill', methods=['GET', 'POST'])
def paybill():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = db.session.get(User, session['user_id'])
    
    bill_type_key = request.args.get('type', 'electricity')
    
    # Map the URL param to a nice display title
    bill_titles = {
        'electricity': 'Electricity',
        'dth': 'DTH',
        'broadband': 'Landline / Broadband',
        'gas': 'Gas',
        'water': 'Water'
    }
    bill_type_display = bill_titles.get(bill_type_key, 'Electricity')
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        consumer = request.form.get('consumer')
        method = request.form.get('method')
        
        if amount > 0 and amount <= user.balance:
            user.balance -= amount
            txn = Transaction(amount=amount, type=f'{bill_type_display} Bill - {consumer} via {method}', user_id=user.id)
            db.session.add(txn)
            db.session.commit()
            flash(f'Successfully paid ₹{amount} for {bill_type_display} bill.', 'success')
            return redirect(url_for('success_page'))
        else:
            flash('Insufficient balance or invalid amount!', 'error')
            
    return render_template('paybill.html', bill_type=bill_type_display)

@app.route('/recharge', methods=['GET', 'POST'])
def recharge():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = db.session.get(User, session['user_id'])
    
    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        mobile = request.form.get('mobile')
        operator = request.form.get('operator')
        
        if amount > 0 and amount <= user.balance:
            user.balance -= amount
            txn = Transaction(amount=amount, type=f'Mobile Recharge - {mobile} ({operator})', user_id=user.id)
            db.session.add(txn)
            db.session.commit()
            flash(f'Successfully recharged ₹{amount} for {mobile}', 'success')
            return redirect(url_for('success_page'))
        else:
            flash('Insufficient balance or invalid amount!', 'error')
            
    return render_template('recharge.html')

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    user = db.session.get(User, session['user_id'])
    # Get transactions sorted by date descending
    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.date.desc()).all()
    return render_template('history.html', transactions=transactions)

@app.route('/scanpay')
def scanpay():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('scanpay.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        # In a real app, send an email or save to DB
        flash('Message sent successfully! Support will contact you soon.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('contact.html')

@app.route('/success')
def success_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('success.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
