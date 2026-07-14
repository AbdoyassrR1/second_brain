from datetime import datetime
from app.features.reminders.repository import ReminderRepository
from app.features.mail.service import MailService
from .celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_reminder(self, reminder_id):
    repo = ReminderRepository()
    reminder = repo.find_by_id(reminder_id)
    if not reminder:
        return {"error": "Reminder not found", "reminder_id": reminder_id}

    if reminder.is_sent:
        return {"skipped": "Already sent", "reminder_id": reminder_id}

    from app.features.auth.models import User
    from app.features.tasks.models import Task

    user = User.query.get(reminder.user_id)
    task = Task.query.get(reminder.task_id)

    if not user or not task:
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
        raise self.retry(exc=exc)


@celery_app.task
def dispatch_due_reminders():
    repo = ReminderRepository()
    reminders = repo.find_pending(limit=200)
    count = 0
    for reminder in reminders:
        send_reminder.delay(reminder.id)
        count += 1
    return {"dispatched": count}
