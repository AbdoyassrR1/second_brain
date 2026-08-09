#!/usr/bin/python3
"""Tasks repository for database operations."""

from datetime import datetime, date, timedelta, UTC
from sqlalchemy import or_, and_, func, case
from app.extensions import db
from app.shared.database import database
from .models import Task, task_labels


class TaskRepository:
    """Repository for Task database operations."""

    @staticmethod
    def find_by_id(task_id):
        """Find task by ID (including soft-deleted)."""
        return Task.query.filter_by(id=task_id).first()

    @staticmethod
    def find_by_ids(task_ids):
        """Find tasks by IDs (including soft-deleted/archived/foreign).

        Used by the time-tracking validation so the caller can classify each
        id as not_found / foreign / soft_deleted / archived.
        """
        if not task_ids:
            return []
        return Task.query.filter(Task.id.in_(task_ids)).all()

    @staticmethod
    def find_active_by_id(task_id):
        """Find task by ID, excluding soft-deleted."""
        return Task.query.filter_by(id=task_id, is_deleted=False).first()

    @staticmethod
    def find_by_user_id(
        user_id,
        status=None,
        priority=None,
        project_id=None,
        parent_task_id=None,
        due=None,
        overdue=None,
        q=None,
        labels=None,
        include_archived=False,
        archived=None,
        sort=None,
        page=1,
        per_page=20,
    ):
        query = Task.query.filter_by(user_id=user_id, is_deleted=False)

        # Archive filter
        if archived:
            query = query.filter_by(is_archived=True)
        elif not include_archived:
            query = query.filter_by(is_archived=False)

        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority=priority)
        if project_id is not None:
            query = query.filter_by(project_id=project_id)
        if parent_task_id is not None:
            if parent_task_id == "none":
                query = query.filter(Task.parent_task_id.is_(None))
            else:
                query = query.filter_by(parent_task_id=parent_task_id)

        # Due date filters
        today = date.today()
        if due == "today":
            query = query.filter(Task.due_date == today)
        elif due == "tomorrow":
            query = query.filter(Task.due_date == today + timedelta(days=1))
        elif due == "upcoming":
            query = query.filter(Task.due_date >= today)

        if overdue:
            query = query.filter(
                and_(
                    Task.due_date < today,
                    Task.status != "completed",
                    Task.status != "cancelled",
                )
            )

        # Search query
        if q:
            search_term = f"%{q}%"
            query = query.filter(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term),
                )
            )

        # Label filter
        if labels:
            label_ids = [l.strip() for l in labels.split(",") if l.strip()]
            if label_ids:
                query = query.filter(
                    Task.labels.any(
                        task_labels.c.label_id.in_(label_ids)
                    )
                )

        # Sorting
        if sort:
            sort_fields = sort.split(",")
            order_criteria = []
            for field in sort_fields:
                field = field.strip()
                if not field:
                    continue
                descending = field.startswith("-")
                clean_field = field.lstrip("-")

                sort_map = {
                    "title": Task.title,
                    "status": Task.status,
                    "priority": Task.priority,
                    "due_date": Task.due_date,
                    "created_at": Task.created_at,
                    "updated_at": Task.updated_at,
                    "completed_at": Task.completed_at,
                }

                if clean_field in sort_map:
                    col = sort_map[clean_field]
                    if descending:
                        order_criteria.append(col.desc().nullslast())
                    else:
                        order_criteria.append(col.asc().nullslast())

            if order_criteria:
                query = query.order_by(*order_criteria)

        return db.paginate(query, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def create(user_id, title, **kwargs):
        """Create and save a new task."""
        task = Task(user_id=user_id, title=title, **kwargs)
        database.add(task)
        database.commit()
        return task

    @staticmethod
    def update(task_id, **kwargs):
        """Update task fields."""
        task = Task.query.filter_by(id=task_id).first()
        if task and kwargs:
            for key, value in kwargs.items():
                if hasattr(task, key) and key not in ["id", "user_id", "created_at"]:
                    setattr(task, key, value)
            database.commit()
        return task

    @staticmethod
    def soft_delete(task_id):
        """Soft delete a task by setting is_deleted and deleted_at."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_deleted = True
            task.deleted_at = datetime.now(UTC)
            database.commit()
            return True
        return False

    @staticmethod
    def restore(task_id):
        """Restore a soft-deleted task."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_deleted = False
            task.deleted_at = None
            database.commit()
            return True
        return False

    @staticmethod
    def archive(task_id):
        """Archive a task."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_archived = True
            task.archived_at = datetime.now(UTC)
            database.commit()
            return True
        return False

    @staticmethod
    def restore_archive(task_id):
        """Restore a task from archive."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_archived = False
            task.archived_at = None
            database.commit()
            return True
        return False

    @staticmethod
    def delete(task_id):
        """Permanently delete a task."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            database.delete(task)
            database.commit()
            return True
        return False

    @staticmethod
    def count_by_user(user_id):
        """Count tasks for a user (excluding soft-deleted)."""
        return Task.query.filter_by(user_id=user_id, is_deleted=False).count()

    @staticmethod
    def get_subtasks(parent_task_id):
        """Get subtasks for a parent task (excluding soft-deleted)."""
        return Task.query.filter_by(
            parent_task_id=parent_task_id,
            is_deleted=False,
        ).all()

    @staticmethod
    def bulk_update(task_ids, user_id, **kwargs):
        """Bulk update tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        if tasks and kwargs:
            for task in tasks:
                for key, value in kwargs.items():
                    if hasattr(task, key) and key not in ["id", "user_id", "created_at"]:
                        setattr(task, key, value)
            database.commit()
        return tasks

    @staticmethod
    def bulk_soft_delete(task_ids, user_id):
        """Bulk soft delete tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        now = datetime.now(UTC)
        for task in tasks:
            task.is_deleted = True
            task.deleted_at = now
        database.commit()
        return tasks

    @staticmethod
    def bulk_archive(task_ids, user_id):
        """Bulk archive tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        now = datetime.now(UTC)
        for task in tasks:
            task.is_archived = True
            task.archived_at = now
        database.commit()
        return tasks

    @staticmethod
    def bulk_restore(task_ids, user_id):
        """Bulk restore soft-deleted tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == True,
        ).all()
        for task in tasks:
            task.is_deleted = False
            task.deleted_at = None
        database.commit()
        return tasks

    @staticmethod
    def bulk_restore_archive(task_ids, user_id):
        """Bulk restore archived tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        for task in tasks:
            task.is_archived = False
            task.archived_at = None
        database.commit()
        return tasks

    @staticmethod
    def bulk_complete(task_ids, user_id):
        """Bulk complete tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        now = datetime.now(UTC)
        for task in tasks:
            task.status = "completed"
            task.completed_at = now
        database.commit()
        return tasks

    @staticmethod
    def get_statistics(user_id):
        """Get task statistics for a user.

        Args:
            user_id: User ID

        Returns:
            dict: Statistics data
        """
        today = date.today()

        # Base query: non-deleted tasks
        base = Task.query.filter_by(user_id=user_id, is_deleted=False)

        # Single aggregation query for all summary counts.
        # NOTE: MySQL does not support `count() FILTER (WHERE ...)`, so use
        # portable `count(case((cond, 1)))` — counts only rows where cond is true.
        row = database.session.query(
            func.count().label("total"),
            func.count(case((Task.status.in_(["todo", "in_progress"]), 1))).label("active"),
            func.count(case((Task.status == "completed", 1))).label("completed"),
            func.count(case((Task.is_archived == True, 1))).label("archived"),
            func.count(case((and_(
                Task.due_date < today,
                Task.status.notin_(["completed", "cancelled"]),
            ), 1))).label("overdue"),
            func.count(case((and_(
                Task.due_date == today,
                Task.status.notin_(["completed", "cancelled"]),
            ), 1))).label("due_today"),
        ).filter(
            Task.user_id == user_id, Task.is_deleted == False
        ).first()

        total_tasks = row.total
        active_tasks = row.active
        completed_tasks = row.completed
        archived_tasks = row.archived
        overdue_tasks = row.overdue
        due_today_tasks = row.due_today

        # GROUP BY for status and priority counts (2 queries instead of 8)
        status_rows = base.with_entities(Task.status, func.count().label("cnt")).group_by(Task.status).all()
        status_counts = {r.status: r.cnt for r in status_rows}

        priority_rows = base.with_entities(Task.priority, func.count().label("cnt")).group_by(Task.priority).all()
        priority_counts = {r.priority: r.cnt for r in priority_rows}

        # Completion rate
        completion_rate = 0.0
        if total_tasks > 0:
            completion_rate = round((completed_tasks / total_tasks) * 100, 2)

        return {
            "total_tasks": total_tasks,
            "active_tasks": active_tasks,
            "completed_tasks": completed_tasks,
            "archived_tasks": archived_tasks,
            "overdue_tasks": overdue_tasks,
            "due_today_tasks": due_today_tasks,
            "tasks_by_status": status_counts,
            "tasks_by_priority": priority_counts,
            "completion_rate": completion_rate,
        }