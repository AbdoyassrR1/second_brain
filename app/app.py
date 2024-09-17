from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from flasgger import Swagger


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(get_remote_address, default_limits=["200 per day", "50 per hour"])
bcrypt = Bcrypt()
swagger = Swagger()

def create_app():
    app = Flask(__name__)

    # Initialize the app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    bcrypt.init_app(app)
    swagger.init_app(app)


    from app.models.user import User
    from app.models.habit import Habit, HabitEntry
    from app.models.task import Task

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
