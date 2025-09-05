# inventory_management/main.py

from flask import Flask
from extensions import db, login_manager
from flask_mail import Mail
import os
from datetime import datetime

# Mail অবজেক্ট তৈরি করা
mail = Mail()

def create_app():
    app = Flask(__name__)
    @app.context_processor
    def inject_year():
        return {'current_year': datetime.utcnow().year}

    # User loader function
    from models.user import User

    # Configuration
    app.config['SECRET_KEY'] = 'your_super_secret_key_12345_change_it'
    
    # Database Configuration
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, 'database', 'inventory.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Flask-Mail Configuration (নতুন অংশ) ---
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    # আপনার Gmail ইউজারনেম এবং App Password এখানে দিন
    app.config['MAIL_USERNAME'] = 'rajadkumar70@gmail.com'  
    app.config['MAIL_PASSWORD'] = 'tsii gwxb noki bkov' # Google App Password
    app.config['MAIL_DEFAULT_SENDER'] = 'rajadkumar70@gmail.com'
    
    # Extensions Initialization
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app) # অ্যাপের সাথে mail অবজেক্টটি যুক্ত করা

    login_manager.login_view = 'app_routes.login'
    login_manager.login_message_category = 'info'

    # User loader function
    from models.user import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprint রেজিস্টার করা
    from ui.web_app import app_routes
    app.register_blueprint(app_routes)

    # অ্যাপ Context এর মধ্যে ডাটাবেস টেবিল তৈরি করা
    with app.app_context():
        db.create_all()
        print("Database tables created successfully.")

    return app

# --- Gunicorn-এর জন্য এই লাইনটি যোগ করা হয়েছে ---
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
