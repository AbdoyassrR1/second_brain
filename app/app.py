from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.habits.routes import habits_bp
from app.tasks.routes import tasks_bp
from app.finances.routes import finances_bp

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    
    # Configure the app (set database URI, secret key, etc.)
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqldb://root:RootPass!12@localhost/second_brain"
    app.config['SECRET_KEY'] = 'your-secret-key'

    # Initialize the database
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(habits_bp, url_prefix='/habits')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(finances_bp, url_prefix='/finances')

    return app
