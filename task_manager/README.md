# Task Manager (FastAPI)

Features: JWT auth (HttpOnly cookie), task CRUD, subtasks, priority/status/due date/category/tags,
search + filters + sorting + pagination, recurring tasks, overdue highlighting, dashboard stats,
Kanban drag-and-drop, dark mode, CSV/JSON export, activity log, per-user data isolation.

## Run locally
```bash
python -m venv venv && source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # set SECRET_KEY
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000 and register an account. API docs: /docs

## Tests
`pytest -q`

## Docker
`docker compose up --build` then open http://localhost:8000

## API
| Method | Path | Purpose |
|---|---|---|
| POST | /api/register, /api/login, /api/logout | Auth |
| GET/POST | /api/tasks | List (q,status,priority,category,tag,due_from,due_to,sort,page,size) / create |
| PATCH/DELETE | /api/tasks/{id} | Update / delete |
| POST | /api/tasks/{id}/subtasks | Add subtask |
| PATCH | /api/tasks/{id}/subtasks/{sid} | Toggle subtask |
| GET | /api/stats | Dashboard numbers |
| GET | /api/export?format=csv\|json | Export |
| GET | /api/activity | Recent activity |

## Screenshots
Add yours here.
