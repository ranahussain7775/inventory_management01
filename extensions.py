# inventory_management/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail # <-- This line is new

# ডাটাবেস, লগইন ম্যানেজার এবং মেইল অবজেক্ট এখানে তৈরি করুন
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail() # <-- This line is new
