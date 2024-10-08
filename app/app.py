from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from flasgger import Swagger
from os import getenv


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(get_remote_address, default_limits=["200 per day", "50 per hour"])
bcrypt = Bcrypt()
swagger = Swagger()

def create_app():
    app = Flask(__name__)


    DB_USER = getenv(DB_USER)
    DB_PASSWORD = getenv(DB_PASSWORD)
    DB_HOST = getenv(DB_HOST)
    DB_NAME = getenv(DB_NAME)
    SECRET_KEY = getenv(SECRET_KEY)

    # Configure the app (set database URI, secret key, etc.)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    app.config['SECRET_KEY'] = SECRET_KEY

    # Initialize the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    bcrypt.init_app(app)
    swagger.init_app(app)


    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # import Blueprints
    from app.views.auth.auth import auth
    from app.views.auth.profile import profile
    from app.views.tasks.tasks import tasks
    from app.views.habits.habits import habits
    from app.views.habits.habit_entries import habit_entries
    from app.views.finances.finances import finances

    # Register blueprints
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(profile, url_prefix="/profile")
    app.register_blueprint(tasks, url_prefix="/tasks")
        # Nesting Blueprints
    habits.register_blueprint(habit_entries, url_prefix="/habit_entries")
    app.register_blueprint(habits, url_prefix="/habits")
    app.register_blueprint(finances, url_prefix="/finances")

    return app
