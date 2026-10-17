from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost:3306/flask_chapter_4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'password'

db = SQLAlchemy(app)

class StockInventory(db.Model):
    stockID = db.Column(db.Integer, nullable=False, primary_key=True)
    companyID = db.Column(db.Integer, nullable=False, foreign_key=True)
    adminID = db.Column(db.Integer, nullable=False, foreign_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    ticker = db.Column(db.String(4), nullable=False)
    quantity = db.Column(db.Float, nullable=True)
    initStockPrice = db.Column(db.Float, nullable=False)
    currentMarketPrice = db.Column(db.Float, nullable=False)

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
    custPassword = db.Column(db.String, nullable=False)
    availableFunds = db.Column(db.Float, nullable=False)

class Administrator(db.Model):
    adminID = db.Column(db.Integer, nullable=False, primary_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    fullName = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    adminPassword = db.Column(db.String(255), nullable=False)

class Portfolio(db.Model):
    portfolioID = db.Column(db.Integer, nullable=False, primary_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    customerID = db.Column(db.Integer, foreign_key=True)
    stockID = db.Column(db.Integer, nullable=False, foreign_key=True)

class OrderHistory(db.Model):
    orderID = db.Column(db.Integer, nullable=False, primary_key=True)
    stockID = db.Column(db.Integer, nullable=False, foreign_key=True)
    customerID = db.Column(db.Integer, nullable=False, foreign_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    updatedAt = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(8), nullable=False)
    tradeType = db.Column(db.String(4), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    totalValue = db.Column(db.Float, nullable=False)

class FinancialTransaction(db.Model):
    transactionID = db.Column(db.Integer, nullable=False, primary_key=True)
    companyID = db.Column(db.Integer, nullable=False, foreign_key=True)
    orderID = db.Column(db.Integer, nullable=False, foreign_key=True)
    createdAt = db.Column(db.DateTime, nullable=False)
    accountNum = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    stocks = StockInventory.query.all() 
    return render_template('home.html', stocks=stocks)