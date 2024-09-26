# Second Brain

## Project Overview

**Second Brain** is a web application designed to help users manage various aspects of their life, including tasks, finances, and habits. The application features user authentication, secure data management, and an intuitive interface for tracking progress over time.

## Features

- **User Authentication**: Secure login with session management.
- **Task Management**: Create, read, update, and delete tasks, with filtering by status, category, and priority.
- **Habit Tracking**: Manage and track personal habits through dedicated endpoints.
- **Financial Management**: Organize financial transactions with the ability to generate statistics.
- **API Documentation**: Detailed API specifications using Swagger for easy integration.
- **Rate Limiting**: Protect the API from excessive requests.

## Technologies Used

- **Backend Framework**: Flask
- **Database**: MySQL (with SQLAlchemy and Flask-SQLAlchemy)
- **User Authentication**: Flask-Login
- **Password Hashing**: Flask-Bcrypt
- **API Documentation**: Flasgger (Swagger UI)
- **Rate Limiting**: Flask-Limiter
- **Database Migration**: Flask-Migrate

## File Structure

```
second_brain/
├── README.md
├── app/
│   ├── __init__.py
│   ├── app.py
│   ├── migrations/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── finance.py
│   │   ├── habit.py
│   │   ├── task.py
│   │   └── user.py
│   └── views/
│       ├── __init__.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── auth.py
│       │   └── profile.py
│       ├── docs/
│       ├── finances/
│       │   ├── __init__.py
│       │   └── finances.py
│       ├── habits/
│       │   ├── __init__.py
│       │   ├── habit_entries.py
│       │   └── habits.py
│       └── tasks/
│           ├── __init__.py
│           └── tasks.py
└── run.py
```

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd second_brain
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the database connection in `app/app.py`:
   ```python
   app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqldb://<username>:<password>@localhost/second_brain"
   ```

4. Run database migrations:
   ```bash
   flask db upgrade
   ```

5. Start the application:
   ```bash
   python run.py
   ```

## API Endpoints

### Task Management
- **GET /tasks/**
  - Description: Retrieve all tasks related to the logged-in user.
  - Filters: Supports filtering by search, status, category, and priority.

- **POST /tasks/create_task**
  - Description: Create a new task for the logged-in user.
  - Required Fields: `title`, `status`, `priority`, and `category`.

- **PATCH /tasks/update_task/<task_id>**
  - Description: Update an existing task.
  - Valid Fields: `title`, `description`, `status`, `priority`, and `category`.

- **DELETE /tasks/delete_task/<task_id>**
  - Description: Delete a task for the logged-in user.

### Habit Management
- **GET /habits/**
  - Description: Retrieve all habits related to the logged-in user.

- **POST /habits/create_habit**
  - Description: Create a new habit.

- **PATCH /habits/update_habit/<habit_id>**
  - Description: Update an existing habit.

- **DELETE /habits/delete_habit/<habit_id>**
  - Description: Delete a habit.

### Financial Management
- **GET /finances/**
  - Description: Retrieve all financial transactions.

- **POST /finances/add_transaction**
  - Description: Add a new financial transaction.

- **PATCH /finances/update_transaction/<transaction_id>**
  - Description: Update an existing transaction.

- **DELETE /finances/delete_transaction/<transaction_id>**
  - Description: Delete a financial transaction.

- **GET /transaction_stats**
  - Description: Get monthly statistics of the user's financial situation.

## Error Handling

The application provides standardized error handling for various scenarios:

- **400 Bad Request**: Returned when there are validation issues or missing data.
- **401 Unauthorized**: Returned for unauthorized access.
- **404 Not Found**: Returned when a requested resource cannot be found.
- **409 Conflict**: Returned when trying to create a duplicate resource.
- **429 Too Many Requests**: Returned when rate limits are exceeded.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or report issues.
```

This format makes it easier to read and understand the API endpoints and their functionality. You can copy this into your `README.md` file. Let me know if you need further adjustments!
