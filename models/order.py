# inventory_management/models/order.py

from extensions import db
from datetime import datetime

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


    # কাস্টমার ডিলিট করলে তার সব অর্ডারও ডিলিট হয়ে যাবে
    orders = db.relationship('Order', backref='customer', lazy=True, cascade="all, delete-orphan")

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    # --- নতুন কলামটি এখানে যোগ করুন ---
    status = db.Column(db.String(50), nullable=False, default='Pending') # ডিফল্ট স্ট্যাটাস 'Pending'

    total_price = db.Column(db.Float, nullable=False)
    delivery_charge = db.Column(db.Float, default=0)
    
    
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sale_price = db.Column(db.Float, nullable=False) 

    product = db.relationship('Product', backref='order_items', lazy=True)