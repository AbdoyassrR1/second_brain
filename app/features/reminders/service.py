from app.shared.exceptions import NotFoundError, ForbiddenError
from .repository import ReminderRepository


class ReminderService:

    def __init__(self):
        self.repository = ReminderRepository()

    @staticmethod
    def _guard_ownership(reminder, user_id):
        if reminder.user_id != user_id:
            raise ForbiddenError("Not authorized to access this reminder")

    def create_reminder(self, task_id, user_id, reminder_time):
        reminder = self.repository.create(task_id, user_id, reminder_time)
        return reminder

    def get_reminder(self, reminder_id, user_id):
        reminder = self.repository.find_by_id(reminder_id)
        if not reminder:
            raise NotFoundError("Reminder not found")
        self._guard_ownership(reminder, user_id)
        return reminder

    def list_reminders(self, user_id, status=None, page=1, per_page=20):
        return self.repository.find_by_user_id(user_id, status=status, page=page, per_page=per_page)

    def update_reminder(self, reminder_id, user_id, **kwargs):
        reminder = self.repository.find_by_id(reminder_id)
        if not reminder:
            raise NotFoundError("Reminder not found")
        self._guard_ownership(reminder, user_id)
        reminder = self.repository.update(reminder_id, **kwargs)
        return reminder

    def delete_reminder(self, reminder_id, user_id):
        reminder = self.repository.find_by_id(reminder_id)
        if not reminder:
            raise NotFoundError("Reminder not found")
        self._guard_ownership(reminder, user_id)
        self.repository.delete(reminder_id)

    def get_pending_reminders(self, limit=100):
        return self.repository.find_pending(limit=limit)

    def mark_sent(self, reminder_id):
        reminder = self.repository.mark_sent(reminder_id)
        if not reminder:
            raise NotFoundError("Reminder not found")
        return reminder

    def mark_failed(self, reminder_id):
        reminder = self.repository.mark_failed(reminder_id)
        if not reminder:
            raise NotFoundError("Reminder not found")
        return reminder
