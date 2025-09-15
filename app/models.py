from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(100))
    Email = db.Column(db.String(120))
    Number = db.Column(db.String(20))
    Message = db.Column(db.Text)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Hashed Password

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    plan = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    paid = db.Column(db.Boolean, default=False)
    razorpay_order_id = db.Column(db.String(100))  # Store Razorpay order ID
