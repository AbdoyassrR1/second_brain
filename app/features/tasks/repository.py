#!/usr/bin/python3
"""Tasks repository for database operations."""

from datetime import datetime, date, timedelta
from sqlalchemy import or_, and_, func, case
from app.extensions import db
from .models import Task, task_labels


class TaskRepository:
    """Repository for Task database operations."""

    @staticmethod
    def find_by_id(task_id):
        """Find task by ID (including soft-deleted)."""
        return Task.query.filter_by(id=task_id).first()

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
        page_size=20,
    ):
        """Find tasks by user ID with optional filters.

        Args:
            user_id: User ID
            status: Filter by status (todo, in_progress, completed, cancelled)
            priority: Filter by priority (low, medium, high, urgent)
            project_id: Filter by project ID
            parent_task_id: Filter by parent task ID (use "none" for top-level)
            due: Due date filter (today, tomorrow, upcoming)
            overdue: Filter overdue tasks (true)
            q: Search query for title/description
            labels: Filter by label IDs (comma-separated)
            include_archived: Include archived tasks
            archived: Show only archived tasks
            sort: Sort specification (e.g. "priority,-due_date")
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            tuple: (list of Task objects, total count)
        """
        # Base query: exclude soft-deleted tasks
        query = Task.query.filter_by(user_id=user_id, is_deleted=False)

        # Archive filter
        if archived == "true":
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

        if overdue == "true":
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

        # Get total count before pagination
        total = query.count()

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

        # Pagination
        if page_size:
            query = query.limit(page_size)
        if page and page > 1:
            query = query.offset((page - 1) * page_size)

        return query.all(), total

    @staticmethod
    def create(user_id, title, **kwargs):
        """Create and save a new task."""
        task = Task(user_id=user_id, title=title, **kwargs)
        db.session.add(task)
        db.session.commit()
        return task

    @staticmethod
    def update(task_id, **kwargs):
        """Update task fields."""
        task = Task.query.filter_by(id=task_id).first()
        if task and kwargs:
            for key, value in kwargs.items():
                if hasattr(task, key) and key not in ["id", "user_id", "created_at"]:
                    setattr(task, key, value)
            db.session.commit()
        return task

    @staticmethod
    def soft_delete(task_id):
        """Soft delete a task by setting is_deleted and deleted_at."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_deleted = True
            task.deleted_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    @staticmethod
    def restore(task_id):
        """Restore a soft-deleted task."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_deleted = False
            task.deleted_at = None
            db.session.commit()
            return True
        return False

    @staticmethod
    def archive(task_id):
        """Archive a task."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_archived = True
            task.archived_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    @staticmethod
    def restore_archive(task_id):
        """Restore a task from archive."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            task.is_archived = False
            task.archived_at = None
            db.session.commit()
            return True
        return False

    @staticmethod
    def delete(task_id):
        """Permanently delete a task."""
        task = Task.query.filter_by(id=task_id).first()
        if task:
            db.session.delete(task)
            db.session.commit()
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
            db.session.commit()
        return tasks

    @staticmethod
    def bulk_soft_delete(task_ids, user_id):
        """Bulk soft delete tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        now = datetime.utcnow()
        for task in tasks:
            task.is_deleted = True
            task.deleted_at = now
        db.session.commit()
        return tasks

    @staticmethod
    def bulk_archive(task_ids, user_id):
        """Bulk archive tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        now = datetime.utcnow()
        for task in tasks:
            task.is_archived = True
            task.archived_at = now
        db.session.commit()
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
        db.session.commit()
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
        db.session.commit()
        return tasks

    @staticmethod
    def bulk_complete(task_ids, user_id):
        """Bulk complete tasks by IDs, ensuring ownership."""
        tasks = Task.query.filter(
            Task.id.in_(task_ids),
            Task.user_id == user_id,
            Task.is_deleted == False,
        ).all()
        now = datetime.utcnow()
        for task in tasks:
            task.status = "completed"
            task.completed_at = now
        db.session.commit()
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

        total_tasks = base.count()

        active_tasks = base.filter(
            Task.status.in_(["todo", "in_progress"])
        ).count()

        completed_tasks = base.filter_by(status="completed").count()

        archived_tasks = base.filter_by(is_archived=True).count()

        overdue_tasks = base.filter(
            and_(
                Task.due_date < today,
                Task.status != "completed",
                Task.status != "cancelled",
            )
        ).count()

        due_today_tasks = base.filter(
            and_(
                Task.due_date == today,
                Task.status != "completed",
                Task.status != "cancelled",
            )
        ).count()

        # Tasks by status
        status_counts = {}
        for s in ["todo", "in_progress", "completed", "cancelled"]:
            count = base.filter_by(status=s).count()
            if count > 0:
                status_counts[s] = count

        # Tasks by priority
        priority_counts = {}
        for p in ["low", "medium", "high", "urgent"]:
            count = base.filter_by(priority=p).count()
            if count > 0:
                priority_counts[p] = count

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