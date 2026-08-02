from datetime import datetime, UTC, timedelta
from app.features.reminders.repository import ReminderRepository
from app.features.mail.service import MailService
from .celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_reminder(self, reminder_id):
    repo = ReminderRepository()
    reminder = repo.find_by_id(reminder_id)
    if not reminder:
        return {"error": "Reminder not found", "reminder_id": reminder_id}

    if reminder.is_sent == "sent":
        return {"skipped": "Already sent", "reminder_id": reminder_id}

    from app.features.auth.models import User
    from app.features.tasks.models import Task

    user = User.query.get(reminder.user_id)
    task = Task.query.get(reminder.task_id)

    if not user or not task:
        repo.mark_failed(reminder_id)
        return {"error": "User or task not found", "reminder_id": reminder_id}

    mail_service = MailService()
    try:
        mail_service.send_email(
            subject=f"Reminder: {task.title}",
            recipients=[user.email],
            body=f"Reminder for task: {task.title}\n\nStatus: {task.status}\n\nSecond Brain",
        )
        repo.mark_sent(reminder_id)
        return {"sent": True, "reminder_id": reminder_id, "email": user.email}
    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except Exception:
            repo.mark_failed(reminder_id)
            return {"error": "Max retries exceeded", "reminder_id": reminder_id}


@celery_app.task
def dispatch_due_reminders():
    repo = ReminderRepository()
    reminders = repo.find_pending(limit=200)
    count = 0
    for reminder in reminders:
        send_reminder.delay(reminder.id)
        count += 1
    return {"dispatched": count}


@celery_app.task
def cleanup_old_reminders(days=30):
    from app.extensions import db
    from app.features.reminders.models import Reminder

    cutoff = datetime.now(UTC) - timedelta(days=days)
    deleted = Reminder.query.filter(
        Reminder.is_sent == "sent", Reminder.created_at < cutoff
    ).delete()
    db.session.commit()
    return {"deleted": deleted}


@celery_app.task
def daily_summary():
    from app.features.auth.models import User
    from app.features.tasks.repository import TaskRepository
    from app.features.mail.service import MailService

    users = User.query.filter(User.is_deleted.is_(False)).all()
    mail_service = MailService()
    sent = 0
    for user in users:
        p = TaskRepository.find_by_user_id(user.id)
        if p.total == 0:
            continue
        task_lines = "\n".join(
            f"- {t.title} [{t.status}]" for t in p.items
        )
        mail_service.send_email(
            subject="Your Daily Summary — Second Brain",
            recipients=[user.email],
            body=f"Hi {user.username},\n\nYou have {p.total} task(s):\n\n{task_lines}\n\n— Second Brain",
        )
        sent += 1
    return {"summary_sent": sent}
