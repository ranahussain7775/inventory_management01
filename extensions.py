# inventory_management/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# ডাটাবেস এবং লগইন ম্যানেজার অবজেক্ট এখানে তৈরি করুন
db = SQLAlchemy()
login_manager = LoginManager()