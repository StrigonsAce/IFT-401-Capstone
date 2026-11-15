import os
import secrets
import re
import math
from datetime import datetime
from sqlalchemy.engine import URL
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, session, abort
from flask_sqlalchemy import SQLAlchemy


load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

app.config["SQLALCHEMY_DATABASE_URI"] = URL.create(
    drivername="mysql+pymysql",
    username=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"],
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.environ["DB_NAME"],
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Administrator(db.Model):
    adminID = db.Column(db.Integer, nullable=False, primary_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    fullName = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    adminPassword = db.Column(db.String(255), nullable=False)

class Company(db.Model):
    companyID = db.Column(db.Integer, nullable=False, primary_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    ticker = db.Column(db.String(4), nullable=False)
    companyDescription = db.Column(db.String(255), nullable=False)

class Customer(db.Model):
    customerID = db.Column(db.Integer, nullable=False, primary_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    fullName = db.Column(db.String(100), nullable=False)
    accountNum = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    custPassword = db.Column(db.String(255), nullable=False)
    availableFunds = db.Column(db.Float, nullable=False)

class FinancialTransaction(db.Model):
    transactionID = db.Column(db.Integer, nullable=False, primary_key=True)
    companyID = db.Column(db.Integer, db.ForeignKey('company.companyID'), nullable=False)
    orderID = db.Column(db.Integer, db.ForeignKey('order_history.orderID'), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False)
    accountNum = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)

class OrderHistory(db.Model):
    orderID = db.Column(db.Integer, nullable=False, primary_key=True)
    stockID = db.Column(db.Integer, db.ForeignKey('stock_inventory.stockID'), nullable=False)
    customerID = db.Column(db.Integer, db.ForeignKey('customer.customerID'), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    updatedAt = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    status = db.Column(db.String(8), nullable=False)
    tradeType = db.Column(db.String(4), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    totalValue = db.Column(db.Float, nullable=False)

class Portfolio(db.Model):
    portfolioID = db.Column(db.Integer, nullable=False, primary_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    customerID = db.Column(db.Integer, db.ForeignKey('customer.customerID'), nullable=False)
    stockID = db.Column(db.Integer, db.ForeignKey('stock_inventory.stockID'), nullable=False)

class StockInventory(db.Model):
    stockID = db.Column(db.Integer, nullable=False, primary_key=True)
    companyID = db.Column(db.Integer, db.ForeignKey('company.companyID'), nullable=False)
    adminID = db.Column(db.Integer, db.ForeignKey('administrator.adminID'), nullable=False)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    ticker = db.Column(db.String(4), nullable=False)
    quantity = db.Column(db.Float, nullable=True)
    initStockPrice = db.Column(db.Float, nullable=False)
    currentMarketPrice = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    stocks = StockInventory.query.all()
    customer = db.session.get(Customer, session['customer_id']) if 'customer_id' in session else None
    return render_template('home.html', stocks=stocks, customer=customer)

@app.route('/login', methods=['POST'])
def login():

    admin = Administrator.query.filter_by(email=request.form['email']).first()

    if admin and admin.adminPassword == request.form['password']:
        session.clear()
        session['admin_id'] = admin.adminID
        session['role'] = 'admin'

        flash(f'Welcome, {admin.fullName}!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    customer = Customer.query.filter_by(email=request.form['email']).first()
    if customer and customer.custPassword == request.form['password']:
        session.clear()
        session['customer_id'] = customer.customerID
        session['role'] = 'customer'

        flash(f'Welcome, {customer.fullName}!', 'success')
        return redirect(url_for('index'))
    
    flash('Invalid email or password', 'error')
    return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect(url_for('index'))

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    customer = db.session.get(Customer, session['customer_id']) if 'customer_id' in session else None
    if not customer:
        flash('Please log in first', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            stock = db.session.get(StockInventory, int(request.form['stockID']))
            quantity = float(request.form['quantity'])
            if not stock or quantity <= 0:
                flash('Enter a valid stock and quantity', 'error')
                return redirect(url_for('buy'))

            total = quantity * stock.currentMarketPrice
            if quantity > (stock.quantity or 0):
                flash('Not enough shares available', 'error')
                return redirect(url_for('buy'))
            if total > customer.availableFunds:
                flash('Insufficient funds', 'error')
                return redirect(url_for('buy'))

            customer.availableFunds -= total
            stock.quantity -= quantity
            db.session.add(OrderHistory(
                stockID=stock.stockID, customerID=customer.customerID,
                status='complete', tradeType='buy',
                quantity=quantity, totalValue=total))
            db.session.commit()
            flash('Stock purchased successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error buying stock: {str(e)}', 'error')
            return redirect(url_for('buy'))

    return render_template('buy_stock.html', stocks=StockInventory.query.all())

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    customer = db.session.get(Customer, session['customer_id']) if 'customer_id' in session else None
    if not customer:
        flash('Please log in first', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            stock = db.session.get(StockInventory, int(request.form['stockID']))
            quantity = float(request.form['quantity'])
            if not stock or quantity <= 0:
                flash('Enter a valid stock and quantity', 'error')
                return redirect(url_for('sell'))

            orders = OrderHistory.query.filter_by(
                customerID=customer.customerID, stockID=stock.stockID, status='complete').all()
            owned = sum(o.quantity if o.tradeType == 'buy' else -o.quantity for o in orders)
            if quantity > owned:
                flash('You do not own enough shares', 'error')
                return redirect(url_for('sell'))

            total = quantity * stock.currentMarketPrice
            customer.availableFunds += total
            stock.quantity = (stock.quantity or 0) + quantity
            db.session.add(OrderHistory(
                stockID=stock.stockID, customerID=customer.customerID,
                status='complete', tradeType='sell',
                quantity=quantity, totalValue=total))
            db.session.commit()
            flash('Stock sold successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error selling stock: {str(e)}', 'error')
            return redirect(url_for('sell'))

    return render_template('sell_stock.html', stocks=StockInventory.query.all())

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin' or 'admin_id' not in session:
        flash('Administrator access required.', 'error')
        return redirect(url_for('index'))

    logged_admin = db.session.get(
        Administrator, session['admin_id']
    )

    if logged_admin is None:
        session.clear()
        flash('Please log in again.', 'error')
        return redirect(url_for('index'))

    return render_template(
        'admin_dashboard.html',
        logged_admin=logged_admin
    )

@app.route('/admin/stocks/create', methods=['GET', 'POST'])
def admin_create_stock():
    # Check administrator access.
    if session.get('role') != 'admin' or 'admin_id' not in session:
        flash('Administrator access required.', 'error')
        return redirect(url_for('index'))

    admin = db.session.get(Administrator, session['admin_id'])

    if admin is None:
        session.clear()
        return redirect(url_for('index'))

    # Create a token for this form.
    if 'create_stock_token' not in session:
        session['create_stock_token'] = secrets.token_hex(32)

    if request.method == 'POST':
        submitted_token = request.form.get('_csrf', '')

        if not secrets.compare_digest(
            submitted_token,
            session['create_stock_token']
        ):
            abort(400, description='Invalid form token. Reload the form.')

        name = request.form.get('name', '').strip()
        ticker = request.form.get('ticker', '').strip().upper()
        description = request.form.get('description', '').strip()

        # Validate text fields.
        if not name or len(name) > 100:
            flash('Enter a stock name of 1–100 characters.', 'error')
            return redirect(url_for('admin_create_stock'))

        if not re.fullmatch(r'[A-Z]{1,4}', ticker):
            flash('Ticker must contain 1–4 letters.', 'error')
            return redirect(url_for('admin_create_stock'))

        if not description or len(description) > 255:
            flash('Enter a company description of 1–255 characters.', 'error')
            return redirect(url_for('admin_create_stock'))

        # Validate numeric fields on the server.
        try:
            quantity = float(request.form.get('quantity', ''))
            price = float(request.form.get('price', ''))
        except (ValueError, OverflowError):
            flash('Enter valid numbers for quantity and price.', 'error')
            return redirect(url_for('admin_create_stock'))

        if (
            not math.isfinite(quantity)
            or not math.isfinite(price)
            or not 0 < quantity <= 99999999.99
            or not 0 < price <= 99999999.99
        ):
            flash(
                'Quantity and price must be greater than zero '
                'and no more than 99,999,999.99.',
                'error'
            )
            return redirect(url_for('admin_create_stock'))

        try:
            # Prevent duplicate tickers in normal form submissions.
            existing_stock = StockInventory.query.filter_by(
                ticker=ticker
            ).first()

            if existing_stock:
                flash('A stock with that ticker already exists.', 'error')
                return redirect(url_for('admin_create_stock'))

            now = datetime.utcnow()

            company = Company.query.filter_by(ticker=ticker).first()

            # Reuse an existing company, or create a new one.
            if company is None:
                company = Company(
                    createdAt=now,
                    updatedAt=now,
                    ticker=ticker,
                    companyDescription=description
                )
                db.session.add(company)

                # Get companyID before creating its stock.
                db.session.flush()

            stock = StockInventory(
                companyID=company.companyID,
                adminID=admin.adminID,
                createdAt=now,
                updatedAt=now,
                name=name,
                ticker=ticker,
                quantity=quantity,
                initStockPrice=price,
                currentMarketPrice=price
            )

            db.session.add(stock)
            db.session.commit()

        except Exception:
            db.session.rollback()
            app.logger.exception('Stock creation failed')
            flash('Could not create the stock. Check the server log.', 'error')
            return redirect(url_for('admin_create_stock'))

        session.pop('create_stock_token', None)
        flash(f'{ticker} created successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template(
        'admin_create_stock.html',
        form_token=session['create_stock_token']
    )
