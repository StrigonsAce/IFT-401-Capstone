import os
import secrets
import re
import math
import random
from datetime import datetime
from sqlalchemy.engine import URL
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from market_utils import get_market_status


load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt(app)
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
    market_open = db.Column(db.Float, nullable=False, default=9.0)
    market_close = db.Column(db.Float, nullable=False, default=17.0)

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

# hours from database or default 9 AM to 5PM
@app.context_processor
def inject_market_status():
    admin = Administrator.query.first()
    open_hour = admin.market_open if admin else 9.0
    close_hour = admin.market_close if admin else 17.0
    return dict(market_info=get_market_status(open_hour, close_hour))
def is_market_open():
    admin = Administrator.query.first()
    open_hour = admin.market_open if admin else 9.0
    close_hour = admin.market_close if admin else 17.0
    return get_market_status(open_hour, close_hour)

def randomize_stock_prices():
    # check if the market is open first
    admin = Administrator.query.first()
    open_hour = admin.market_open if admin else 9.0
    close_hour = admin.market_close if admin else 17.0
    market_info = get_market_status(open_hour, close_hour)
    if not market_info["is_open"]:
        return

    now = datetime.now()
    try:
        stocks = StockInventory.query.all()
        for stock in stocks:
            # change once every 30 seconds
            if (now - stock.updatedAt).total_seconds() >= 30:
                # random percent per stock
                percent = random.uniform(-5, 10)
                change = stock.currentMarketPrice * percent / 100
                new_price = round(stock.currentMarketPrice + change, 2)

                # prevent price from going negative
                if new_price < 0.01:
                    new_price = 0.01

                stock.currentMarketPrice = new_price
                stock.updatedAt = now
        db.session.commit()
    except Exception:
        db.session.rollback()

@app.route('/')
def index():
    randomize_stock_prices()
    stocks = StockInventory.query.all()
    customer = db.session.get(Customer, session['customer_id']) if 'customer_id' in session else None

    total_value = 0
    if customer:
        orders = OrderHistory.query.filter_by(customerID=customer.customerID, status='complete').all()
        stock_totals = {}
        for order in orders:
            if order.stockID not in stock_totals:
                stock_totals[order.stockID] = 0
            if order.tradeType == 'buy':
                stock_totals[order.stockID] += order.quantity
            else:
                stock_totals[order.stockID] -= order.quantity
        
        for stock_id, quantity in stock_totals.items():
            if quantity > 0:
                stock = db.session.get(StockInventory, stock_id)
                if stock:
                    total_value += quantity * stock.currentMarketPrice

    return render_template('home.html', stocks=stocks, customer=customer, total_value=total_value)

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
    try:
        # check password against hashed password
        password_ok = customer and bcrypt.check_password_hash(
            customer.custPassword, request.form['password'])
    except ValueError:
        # no plain text passwords
        password_ok = False

    if password_ok:
        session.clear()
        session['customer_id'] = customer.customerID
        session['role'] = 'customer'

        flash(f'Welcome, {customer.fullName}!', 'success')
        return redirect(url_for('index'))
    
    flash('Invalid email or password', 'error')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['fullName'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        if not full_name or not email or not password:
            flash('fill in all fields', 'error')
            return redirect(url_for('register'))

        # unique email check
        existing_customer = Customer.query.filter_by(email=email).first()
        existing_admin = Administrator.query.filter_by(email=email).first()
        if existing_customer or existing_admin:
            flash('This email already exists', 'error')
            return redirect(url_for('register'))

        try:
            # generate random 8-digit account number
            account_num = str(random.randint(11111111, 99999999))
            while Customer.query.filter_by(accountNum=account_num).first():
                account_num = str(random.randint(11111111, 99999999))

            # only the hashed password is stored
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            now = datetime.now()
            db.session.add(Customer(
                createdAt=now, updatedAt=now,
                fullName=full_name, accountNum=account_num,
                email=email, custPassword=hashed_password,
                availableFunds=0))
            db.session.commit()
            flash('Account created. Please log in.', 'success')
            return redirect(url_for('index'))
        except Exception:
            db.session.rollback()
            flash('Could not create the account', 'error')
            return redirect(url_for('register'))

    return render_template('sign_up.html')

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

    # market = is_market_open()
    # if not market['is_open']:
    #     flash('Market is currently closed.', 'error')
    #     return redirect(url_for('index'))

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

    randomize_stock_prices()
    return render_template('buy_stock.html', stocks=StockInventory.query.all())

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    customer = db.session.get(Customer, session['customer_id']) if 'customer_id' in session else None
    if not customer:
        flash('Please log in first', 'error')
        return redirect(url_for('index'))

    # market = is_market_open()
    # if not market['is_open']:
    #     flash('Market is currently closed.', 'error')
    #     return redirect(url_for('index'))

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

    randomize_stock_prices()
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

    randomize_stock_prices()
    stocks = StockInventory.query.all()

    orders = OrderHistory.query.filter_by(status='complete').order_by(OrderHistory.createdAt.desc()).all()
    history_data = []
    for order in orders:
        stock = db.session.get(StockInventory, order.stockID)
        history_data.append({
            'date': order.createdAt.strftime('%Y-%m-%d %I:%M %p'),
            'type': order.tradeType.capitalize(),
            'ticker': stock.ticker if stock else 'Unknown',
            'quantity': order.quantity,
            'totalValue': order.totalValue
        })

    return render_template(
        'admin_dashboard.html',
        logged_admin=logged_admin,
        stocks=stocks,
        history=history_data
    )

@app.route('/admin/market_hours', methods=['POST'])
def update_market_hours():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    admin = db.session.get(Administrator, session['admin_id'])

    new_open = float(request.form['open_hour'])
    new_close = float(request.form['close_hour'])
    admin.market_open = new_open
    admin.market_close = new_close
    db.session.commit()
    flash('Market hours updated', 'success')
    return redirect(url_for('admin_dashboard'))


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

            now = datetime.now()

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

@app.route('/balance', methods=['GET', 'POST'])
def balance():
    customer = db.session.get(Customer, session['customer_id']) if 'customer_id' in session else None
    if not customer:
        flash('Please log in first', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            amount = float(request.form['updateFunds'])
            update_type = request.form['updateType']

            if amount <= 0:
                flash('Enter a valid amount', 'error')
                return redirect(url_for('balance'))

            if update_type == 'Deposit':
                customer.availableFunds += amount
                flash('Funds deposited successfully!', 'success')
            elif update_type == 'Withdraw':
                if amount > customer.availableFunds:
                    flash('Not enough funds in balance', 'error')
                    return redirect(url_for('balance'))
                customer.availableFunds -= amount
                flash('Funds withdrawn successfully!', 'success')
            else:
                flash('Invalid transaction type', 'error')
                return redirect(url_for('balance'))

            db.session.commit()
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating funds: {str(e)}', 'error')
            return redirect(url_for('balance'))

    return render_template('balance.html', customer=customer)

@app.route('/portfolio')
#logged in first?
def portfolio():
    customer = db.session.get(Customer, session['customer_id']) if 'customer_id' in session else None
    if not customer:
        flash('Log in first.', 'error')
        return redirect(url_for('index'))
    orders = OrderHistory.query.filter_by(customerID=customer.customerID, status='complete').all()
    stock_totals = {}
    for order in orders:
        if order.stockID not in stock_totals:
            stock_totals[order.stockID] = 0
        if order.tradeType == 'buy':
            stock_totals[order.stockID] += order.quantity
        else:
            stock_totals[order.stockID] -= order.quantity
    #currently owned stocks
    my_stocks = []
    total_value = 0
    for stock_id, quantity in stock_totals.items():
        if quantity > 0:
            stock = db.session.get(StockInventory, stock_id)
            if stock:
                total_value += quantity * stock.currentMarketPrice
                my_stocks.append({
                    'ticker': stock.ticker,
                    'name': stock.name,
                    'quantity': quantity,
                    'currentMarketPrice': stock.currentMarketPrice
                })
    history_data = []
    for order in orders:
        stock = db.session.get(StockInventory, order.stockID)
        history_data.append({
            'date': order.createdAt.strftime('%Y-%m-%d %I:%M %p'),
            'type': order.tradeType.capitalize(),
            'ticker': stock.ticker if stock else 'Unknown',
            'quantity': order.quantity,
            'totalValue': order.totalValue
        })
    
    return render_template('portfolio.html', my_stocks=my_stocks, history=history_data, total_value=total_value, customer=customer)