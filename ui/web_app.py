# inventory_management/ui/web_app.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, mail # <-- This import has been changed
from models.user import User
from models.product import Product
from models.supplier import Supplier, SupplierPayment
from models.order import Customer, Order, OrderItem
from datetime import datetime, timedelta, date
import os
import secrets
import random
from werkzeug.utils import secure_filename

# নতুন ফিচারগুলোর জন্য প্রয়োজনীয় ইম্পোর্ট
# from main import mail <-- This incorrect line is removed
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

app_routes = Blueprint('app_routes', __name__)

# টোকেন তৈরির জন্য Serializer (Secret Key টি পরিবর্তন করে নেবেন)
s = URLSafeTimedSerializer('A-VERY-SECRET-KEY-FOR-OTP-AND-RESET')

# --- Helper Function for Image Saving ---
def save_product_image(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/uploads', picture_fn)
    form_picture.save(picture_path)
    return picture_fn

# ==============================================================================
# --- Authentication Routes (Updated with OTP & Forgot Password) ---
# ==============================================================================

@app_routes.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('app_routes.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'warning')
            return redirect(url_for('app_routes.register'))

        otp_code = f"{random.randint(100000, 999999)}"
        otp_expiry_time = datetime.utcnow() + timedelta(minutes=10)

        new_user = User(
            username=username, 
            email=email, 
            otp=otp_code, 
            otp_expiry=otp_expiry_time
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        try:
            token = s.dumps(email, salt='email-confirm')
            msg = Message('Confirm Your Email for Inventory Pro', recipients=[email])
            link = url_for('app_routes.verify_email', token=token, _external=True)
            msg.body = f'Welcome! Your verification code is: {otp_code}\n\nAlternatively, you can click the following link: {link}\nThis code will expire in 10 minutes.'
            msg.html = render_template('email/verification_email.html', otp_code=otp_code, link=link)
            mail.send(msg)
            flash('A verification code and link have been sent to your email.', 'info')
        except Exception as e:
            flash(f'Could not send email. Please check your configuration. Error: {str(e)}', 'danger')
        
        return redirect(url_for('app_routes.enter_otp', email=email))
    return render_template('register.html')

@app_routes.route('/enter-otp', methods=['GET', 'POST'])
def enter_otp():
    email = request.args.get('email')
    if not email:
        return redirect(url_for('app_routes.register'))

    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('app_routes.register'))

        if user.otp == submitted_otp and datetime.utcnow() < user.otp_expiry:
            user.is_verified = True
            user.otp = None
            user.otp_expiry = None
            db.session.commit()
            flash('Your email has been verified successfully! You can now login.', 'success')
            return redirect(url_for('app_routes.login'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
    return render_template('enter_otp.html', email=email)

@app_routes.route('/verify_email/<token>')
def verify_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        flash('The verification link has expired.', 'danger')
        return redirect(url_for('app_routes.login'))
    except Exception:
        flash('The verification link is invalid.', 'danger')
        return redirect(url_for('app_routes.login'))
    
    user = User.query.filter_by(email=email).first_or_404()
    if user.is_verified:
        flash('Account already verified. Please login.', 'info')
    else:
        user.is_verified = True
        user.otp = None
        user.otp_expiry = None
        db.session.commit()
        flash('Your email has been verified! You can now login.', 'success')
    return redirect(url_for('app_routes.login'))

@app_routes.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('app_routes.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.is_verified:
                login_user(user)
                return redirect(url_for('app_routes.dashboard'))
            else:
                flash('Please verify your email address first.', 'warning')
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app_routes.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            try:
                token = s.dumps(email, salt='password-reset')
                msg = Message('Password Reset Request', recipients=[email])
                link = url_for('app_routes.reset_password', token=token, _external=True)
                msg.body = f'Click the link to reset your password: {link}. This link will expire in 1 hour.'
                msg.html = f'<h3>Password Reset</h3><p>Please click the button below to reset your password.</p><a href="{link}" style="padding: 10px 20px; background-color: #0d6efd; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a>'
                mail.send(msg)
                flash('A password reset link has been sent to your email.', 'info')
            except Exception as e:
                flash(f'Could not send email. Error: {str(e)}', 'danger')
            return redirect(url_for('app_routes.login'))
        else:
            flash('Email address not found.', 'danger')
    return render_template('forgot_password.html')

@app_routes.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset', max_age=3600)
    except SignatureExpired:
        flash('The password reset link is expired. Please try again.', 'danger')
        return redirect(url_for('app_routes.forgot_password'))
    except Exception:
        flash('The password reset link is invalid.', 'danger')
        return redirect(url_for('app_routes.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first_or_404()
        user.set_password(password)
        db.session.commit()
        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('app_routes.login'))
    return render_template('reset_password.html')

@app_routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('app_routes.login'))

# ==============================================================================
# --- Core App Routes ---
# ==============================================================================

@app_routes.route('/')
@login_required
def dashboard():
    total_products = Product.query.filter_by(user_id=current_user.id).count()
    total_suppliers = Supplier.query.filter_by(user_id=current_user.id).count()
    total_customers = Customer.query.filter_by(user_id=current_user.id).count()
    
    user_products = Product.query.filter_by(user_id=current_user.id).all()
    low_stock_products = [p for p in user_products if p.is_low_stock()]

    top_products_by_stock = Product.query.filter_by(user_id=current_user.id).order_by(Product.quantity.desc()).limit(5).all()
    chart_labels = [p.name for p in top_products_by_stock]
    chart_data = [p.quantity for p in top_products_by_stock]

    recent_products = Product.query.filter_by(user_id=current_user.id).order_by(Product.id.desc()).limit(5).all()

    return render_template('dashboard.html', 
                                total_products=total_products,
                                low_stock_count=len(low_stock_products),
                                low_stock_products=low_stock_products,
                                total_suppliers=total_suppliers,
                                total_customers=total_customers,
                                chart_labels=chart_labels,
                                chart_data=chart_data,
                                recent_products=recent_products
                                )

# ==============================================================================
# --- Product Routes ---
# ==============================================================================

@app_routes.route('/products')
@login_required
def products():
    all_products = Product.query.filter_by(user_id=current_user.id).order_by(Product.id.desc()).all()
    return render_template('products.html', products=all_products)

@app_routes.route('/products/add', methods=['GET', 'POST'])
@login_required
def add_product():
    if request.method == 'POST':
        sku = request.form.get('sku')
        if not sku:
            flash('SKU field cannot be empty.', 'danger')
        elif Product.query.filter_by(sku=sku, user_id=current_user.id).first():
            flash(f'SKU "{sku}" already exists for your account.', 'danger')
        else:
            try:
                image_filename = 'default.png'
                if 'image_file' in request.files:
                    file = request.files['image_file']
                    if file.filename != '':
                        image_filename = save_product_image(file)
                
                new_product = Product(
                    name=request.form['name'], sku=sku, image_file=image_filename,
                    quantity=int(request.form['quantity']),
                    wholesale_price=float(request.form['wholesale_price']),
                    china_delivery_charge=float(request.form['china_delivery_charge']),
                    total_weight=float(request.form['total_weight']),
                    per_weight_cost=float(request.form['per_weight_cost']),
                    bd_delivery_charge=float(request.form['bd_delivery_charge']),
                    supplier_id=int(request.form['supplier_id']) if request.form.get('supplier_id') else None,
                    user_id=current_user.id
                )
                db.session.add(new_product)
                db.session.commit()
                flash('Product added successfully!', 'success')
                return redirect(url_for('app_routes.products'))
            except Exception as e:
                flash(f'Error adding product: {e}', 'danger')
                db.session.rollback()
    suppliers = Supplier.query.filter_by(user_id=current_user.id).all()
    return render_template('add_product.html', suppliers=suppliers)


@app_routes.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    product = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        try:
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file.filename != '':
                    product.image_file = save_product_image(file)

            product.name = request.form['name']
            product.sku = request.form['sku']
            product.quantity = int(request.form['quantity'])
            product.wholesale_price = float(request.form['wholesale_price'])
            product.china_delivery_charge = float(request.form['china_delivery_charge'])
            product.total_weight = float(request.form['total_weight'])
            product.per_weight_cost = float(request.form['per_weight_cost'])
            product.bd_delivery_charge = float(request.form['bd_delivery_charge'])
            product.supplier_id = int(request.form['supplier_id']) if request.form.get('supplier_id') else None
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('app_routes.products'))
        except Exception as e:
            flash(f'Error updating product: {e}', 'danger')
            db.session.rollback()
    suppliers = Supplier.query.filter_by(user_id=current_user.id).all()
    return render_template('edit_product.html', product=product, suppliers=suppliers)

@app_routes.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product_to_delete = Product.query.filter_by(id=product_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(product_to_delete)
        db.session.commit()
        flash('Product deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')
    return redirect(url_for('app_routes.products'))

# ==============================================================================
# --- Supplier Routes ---
# ==============================================================================

@app_routes.route('/suppliers')
@login_required
def suppliers():
    all_suppliers = Supplier.query.filter_by(user_id=current_user.id).all()
    return render_template('suppliers.html', suppliers=all_suppliers)

@app_routes.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
def add_supplier():
    if request.method == 'POST':
        phone = request.form['phone']
        if Supplier.query.filter_by(phone=phone, user_id=current_user.id).first():
            flash(f'Supplier with phone number {phone} already exists.', 'warning')
        else:
            new_supplier = Supplier(
                name=request.form['name'], contact_person=request.form['contact_person'],
                phone=phone, address=request.form['address'], user_id=current_user.id
            )
            db.session.add(new_supplier)
            db.session.commit()
            flash('Supplier added successfully!', 'success')
            return redirect(url_for('app_routes.suppliers'))
    return render_template('add_supplier.html')

@app_routes.route('/suppliers/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
def supplier_details(supplier_id):
    supplier = Supplier.query.filter_by(id=supplier_id, user_id=current_user.id).first_or_404()
    if request.method == 'POST':
        try:
            amount = float(request.form.get('amount'))
            notes = request.form.get('notes')
            payment = SupplierPayment(
                supplier_id=supplier.id, amount=amount,
                payment_date=date.today(), notes=notes
            )
            db.session.add(payment)
            db.session.commit()
            flash('Payment recorded successfully!', 'success')
        except Exception as e:
            flash(f'Error recording payment: {e}', 'danger')
        return redirect(url_for('app_routes.supplier_details', supplier_id=supplier.id))
    return render_template('supplier_details.html', supplier=supplier)

@app_routes.route('/suppliers/delete/<int:supplier_id>', methods=['POST'])
@login_required
def delete_supplier(supplier_id):
    supplier_to_delete = Supplier.query.filter_by(id=supplier_id, user_id=current_user.id).first_or_404()
    if supplier_to_delete.products:
        flash('Cannot delete supplier with associated products. Please reassign or delete them first.', 'danger')
        return redirect(url_for('app_routes.suppliers'))
    try:
        db.session.delete(supplier_to_delete)
        db.session.commit()
        flash('Supplier deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting supplier: {str(e)}', 'danger')
    return redirect(url_for('app_routes.suppliers'))

# ==============================================================================
# --- Customer and Order Routes ---
# ==============================================================================

@app_routes.route('/customers')
@login_required
def customers():
    all_customers = Customer.query.filter_by(user_id=current_user.id).all()
    return render_template('customers.html', customers=all_customers)

@app_routes.route('/customers/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        phone = request.form['phone']
        if Customer.query.filter_by(phone=phone, user_id=current_user.id).first():
            flash(f'The phone number "{phone}" is already registered for your account.', 'danger')
            return redirect(url_for('app_routes.add_customer'))
        new_customer = Customer(name=request.form['name'], phone=phone, address=request.form['address'], user_id=current_user.id)
        db.session.add(new_customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('app_routes.customers'))
    return render_template('add_customer.html')

@app_routes.route('/customers/<int:customer_id>')
@login_required
def customer_details(customer_id):
    customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404()
    return render_template('customer_details.html', customer=customer)

@app_routes.route('/customers/delete/<int:customer_id>', methods=['POST'])
@login_required
def delete_customer(customer_id):
    customer_to_delete = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(customer_to_delete)
        db.session.commit()
        flash('Customer and all associated orders deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'danger')
    return redirect(url_for('app_routes.customers'))


        # এই দুটি নতুন ফাংশন যোগ করুন

@app_routes.route('/orders')
@login_required
def orders_list():
    """সব অর্ডার দেখানোর জন্য পেজ"""
    user_orders = Order.query.join(Customer).filter(Customer.user_id == current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('orders_list.html', orders=user_orders)

@app_routes.route('/orders/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_details(order_id):
    """অর্ডারের বিস্তারিত দেখা এবং স্ট্যাটাস আপডেট করার পেজ"""
    order = Order.query.join(Customer).filter(Customer.user_id == current_user.id, Order.id == order_id).first_or_404()
    
    if request.method == 'POST':
        new_status = request.form.get('status')
        order.status = new_status
        db.session.commit()
        flash(f'Order #{order.id} status has been updated to {new_status}.', 'success')
        return redirect(url_for('app_routes.order_details', order_id=order.id))

    return render_template('order_details.html', order=order)



@app_routes.route('/orders/create', methods=['GET', 'POST'])
@login_required
def create_order():
    if request.method == 'POST':
        try:
            customer_id = int(request.form.get('customer_id'))
            delivery_charge = float(request.form.get('delivery_charge', 0))
            product_ids = request.form.getlist('product_id[]')
            quantities = request.form.getlist('quantity[]')
            sale_prices = request.form.getlist('sale_price[]')
            
            if not product_ids:
                raise Exception("Please add at least one product to the order.")

            customer = Customer.query.filter_by(id=customer_id, user_id=current_user.id).first_or_404()
            total_items_price = 0
            # এখানে স্ট্যাটাস যোগ করুন
            new_order = Order(customer_id=customer.id, delivery_charge=delivery_charge, total_price=0, status=status)
            new_order = Order(customer_id=customer.id, delivery_charge=delivery_charge, total_price=0)
            
            for i in range(len(product_ids)):
                product_id, quantity, sale_price = int(product_ids[i]), int(quantities[i]), float(sale_prices[i])
                product = Product.query.filter_by(id=product_id, user_id=current_user.id).first()
                if not product or product.quantity < quantity:
                    raise Exception(f'Not enough stock for {product.name if product else "selected item"}.')
                product.quantity -= quantity
                order_item = OrderItem(order=new_order, product_id=product_id, quantity=quantity, sale_price=sale_price)
                total_items_price += quantity * sale_price
                db.session.add(order_item)

            new_order.total_price = total_items_price + delivery_charge
            db.session.add(new_order)
            db.session.commit()
            flash('Order created successfully!', 'success')
            return redirect(url_for('app_routes.customer_details', customer_id=customer_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating order: {str(e)}', 'danger')
            
    customers = Customer.query.filter_by(user_id=current_user.id).all()
    products = Product.query.filter_by(user_id=current_user.id).filter(Product.quantity > 0).all()
    return render_template('create_order.html', customers=customers, products=products)

# ==============================================================================
# --- Report Route ---
# ==============================================================================

@app_routes.route('/reports')
@login_required
def reports():
    user_orders = Order.query.join(Customer).filter(Customer.user_id == current_user.id).all()
    order_ids = [order.id for order in user_orders]
    
    total_sales = sum(order.total_price for order in user_orders)
    
    total_cost_of_goods = 0
    if order_ids:
        all_order_items = OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).all()
        for item in all_order_items:
            total_cost_of_goods += item.quantity * item.product.buy_price_per_pcs
            
    profit = total_sales - total_cost_of_goods

    return render_template('reports.html', total_sales=total_sales, total_cost=total_cost_of_goods, profit=profit)
