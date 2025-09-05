# inventory_management/models/product.py

from extensions import db

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(100), unique=True) # Stock Keeping Unit
    quantity = db.Column(db.Integer, default=0)

    image_file = db.Column(db.String(100), nullable=True, default='default.png')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    
    # আপনার দেওয়া কস্টিং ফিল্ডগুলো
    wholesale_price = db.Column(db.Float, default=0)
    china_delivery_charge = db.Column(db.Float, default=0)
    total_weight = db.Column(db.Float, default=0)
    per_weight_cost = db.Column(db.Float, default=0)
    bd_delivery_charge = db.Column(db.Float, default=0)

    # রিলেশনশিপ: কোন সাপ্লায়ারের প্রোডাক্ট
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    supplier = db.relationship('Supplier', backref='products', lazy=True)

    # ডাইনামিকভাবে হিসাব করার জন্য প্রপার্টি
    @property
    def china_to_bd_charge(self):
        return self.total_weight * self.per_weight_cost

    @property
    def total_cost(self):
        product_cost = self.quantity * self.wholesale_price
        return product_cost + self.china_delivery_charge + self.bd_delivery_charge + self.china_to_bd_charge

    @property
    def buy_price_per_pcs(self):
        if self.quantity == 0:
            return 0
        return self.total_cost / self.quantity

    # কম স্টক অ্যালার্টের জন্য
    def is_low_stock(self, threshold=10):
        return self.quantity < threshold