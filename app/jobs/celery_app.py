import os
from datetime import timedelta
from dotenv import load_dotenv
from celery import Celery
from celery.schedules import crontab
from flask import Flask

load_dotenv()

_celery_broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")

celery_app = Celery("second_brain", broker=_celery_broker, backend=_celery_broker)

celery_app.conf.beat_schedule = {
    "dispatch-due-reminders": {
        "task": "app.jobs.tasks.dispatch_due_reminders",
        "schedule": timedelta(seconds=30),
    },
    "cleanup-old-reminders": {
        "task": "app.jobs.tasks.cleanup_old_reminders",
        "schedule": crontab(hour=0, minute=0),
    },
    "daily-summary": {
        "task": "app.jobs.tasks.daily_summary",
        "schedule": crontab(hour=8, minute=0),
    },
}


class FlaskContextTask(celery_app.Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        app = getattr(celery_app, "flask_app", None)
        if app is None:
            from app import create_app
            app = create_app()
            init_celery(app)
        try:
            from flask import has_app_context
            if has_app_context():
                return self.run(*args, **kwargs)
        except ImportError:
            pass
        with app.app_context():
            return self.run(*args, **kwargs)


# Set FlaskContextTask as the default task class now, so tasks registered
# later via @celery_app.task inherit from it.
celery_app.Task = FlaskContextTask
celery_app.conf.include = ["app.jobs.tasks"]


def init_celery(app: Flask, celery_instance: Celery = celery_app) -> Celery:
    celery_instance.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL", _celery_broker),
        result_backend=app.config.get("CELERY_RESULT_BACKEND", _celery_broker),
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_soft_time_limit=300,
        task_time_limit=360,
        task_always_eager=app.config.get("TESTING", False),
    )
    celery_instance.flask_app = app
    return celery_instance
