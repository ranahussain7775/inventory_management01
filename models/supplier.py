from main import db
# আপনার প্রজেক্টের নতুন স্ট্রাকচার অনুযায়ী extensions.py থেকে db ইম্পোর্ট করুন
# from extensions import db

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(150))
    phone = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # রিলেশনশিপ: একজন সাপ্লায়ার অনেক পেমেন্ট পেতে পারে
    payments = db.relationship('SupplierPayment', backref='supplier_payments', lazy=True)

    # সাপ্লায়ারের মোট বকেয়া হিসাব করার জন্য
    @property
    def total_due(self):
        # এই সাপ্লায়ারের কাছ থেকে মোট কত টাকার প্রোডাক্ট কেনা হয়েছে
        total_purchased = sum(p.total_cost for p in self.products)
        # এই সাপ্লায়ারকে মোট কত টাকা পেমেন্ট করা হয়েছে
        total_paid = sum(p.amount for p in self.payments)
        return total_purchased - total_paid

class SupplierPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.String(255))