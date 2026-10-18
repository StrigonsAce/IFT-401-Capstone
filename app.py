from flask import Flask, render_template, redirect, url_for, flash, request, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://student:password@38.254.245.3:3306/projectdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'password'

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
    customer = Customer.query.filter_by(email=request.form['email']).first()
    if customer and customer.custPassword == request.form['password']:
        session.clear()
        session['customer_id'] = customer.customerID
        flash(f'Welcome, {customer.fullName}!', 'success')
    else:
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