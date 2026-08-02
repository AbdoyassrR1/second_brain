from datetime import datetime, UTC
from app.extensions import db
from .models import Reminder


class ReminderRepository:

    @staticmethod
    def find_by_id(reminder_id):
        return Reminder.query.filter_by(id=reminder_id).first()

    @staticmethod
    def find_by_user_id(user_id, status=None, page=1, per_page=20):
        query = Reminder.query.filter_by(user_id=user_id)
        if status is not None:
            query = query.filter_by(is_sent=status)
        query = query.order_by(Reminder.reminder_time.desc())
        return db.paginate(query, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def find_pending(limit=100):
        return (
            Reminder.query.filter_by(is_sent="pending")
            .filter(Reminder.reminder_time <= datetime.now(UTC))
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(task_id, user_id, reminder_time):
        reminder = Reminder(task_id=task_id, user_id=user_id, reminder_time=reminder_time)
        db.session.add(reminder)
        db.session.commit()
        return reminder

    @staticmethod
    def update(reminder_id, **kwargs):
        reminder = Reminder.query.filter_by(id=reminder_id).first()
        if not reminder:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(reminder, key):
                setattr(reminder, key, value)
        db.session.commit()
        return reminder

    @staticmethod
    def delete(reminder_id):
        reminder = Reminder.query.filter_by(id=reminder_id).first()
        if not reminder:
            return None
        db.session.delete(reminder)
        db.session.commit()
        return reminder

    @staticmethod
    def mark_sent(reminder_id):
        reminder = Reminder.query.filter_by(id=reminder_id).first()
        if reminder:
            reminder.is_sent = "sent"
            db.session.commit()
        return reminder

    @staticmethod
    def mark_failed(reminder_id):
        reminder = Reminder.query.filter_by(id=reminder_id).first()
        if reminder:
            reminder.is_sent = "failed"
            db.session.commit()
        return reminder
