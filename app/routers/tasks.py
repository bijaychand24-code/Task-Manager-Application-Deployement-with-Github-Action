"""Task, subtask, stats, export and activity endpoints (all scoped to the current user)."""
import calendar
import csv
import io
import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ActivityLog, Subtask, Task, User
from ..schemas import SubIn, SubPatch, TaskIn, TaskPatch
from ..security import current_user

router = APIRouter(prefix="/api")
PRIO = case({"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}, value=Task.priority)
COLS = ["id", "title", "description", "priority", "status", "due_date", "category", "tags", "recurrence"]


def own_task(db: Session, user: User, tid: int) -> Task:
    t = db.get(Task, tid)
    if not t or t.user_id != user.id:
        raise HTTPException(404, "Task not found")
    return t


def is_overdue(t: Task) -> bool:
    return bool(t.due_date and t.due_date < date.today() and t.status != "Done")


def out(t: Task) -> dict:
    return {
        **{k: getattr(t, k) for k in COLS if k != "due_date"},
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "overdue": is_overdue(t),
        "subtasks": [{"id": s.id, "title": s.title, "done": s.done} for s in t.subtasks],
        "created_at": t.created_at.isoformat(),
    }


def log(db: Session, user: User, tid: int, action: str) -> None:
    db.add(ActivityLog(user_id=user.id, task_id=tid, action=action))


def next_due(d: date | None, rec: str) -> date:
    base = d or date.today()
    if rec == "daily":
        return base + timedelta(days=1)
    if rec == "weekly":
        return base + timedelta(weeks=1)
    y, m = base.year + (base.month == 12), base.month % 12 + 1
    return date(y, m, min(base.day, calendar.monthrange(y, m)[1]))


@router.get("/tasks")
def list_tasks(
    q: str = "", status: str = "", priority: str = "", category: str = "", tag: str = "",
    due_from: date | None = None, due_to: date | None = None, sort: str = "created",
    page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), user: User = Depends(current_user),
):
    qs = db.query(Task).filter(Task.user_id == user.id)
    if q:
        qs = qs.filter(or_(Task.title.ilike(f"%{q}%"), Task.description.ilike(f"%{q}%")))
    if status:
        qs = qs.filter(Task.status == status)
    if priority:
        qs = qs.filter(Task.priority == priority)
    if category:
        qs = qs.filter(Task.category == category)
    if tag:
        qs = qs.filter(Task.tags.ilike(f"%{tag}%"))
    if due_from:
        qs = qs.filter(Task.due_date >= due_from)
    if due_to:
        qs = qs.filter(Task.due_date <= due_to)
    order = {"due": Task.due_date.asc().nulls_last(), "priority": PRIO}.get(sort, Task.created_at.desc())
    total = qs.count()
    items = qs.order_by(order, Task.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "items": [out(t) for t in items]}


@router.post("/tasks", status_code=201)
def create_task(d: TaskIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = Task(user_id=user.id, **d.model_dump())
    db.add(t)
    db.flush()
    log(db, user, t.id, "created")
    db.commit()
    db.refresh(t)
    return out(t)


@router.patch("/tasks/{tid}")
def update_task(tid: int, d: TaskPatch, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = own_task(db, user, tid)
    was_done = t.status == "Done"
    changes = {k: v for k, v in d.model_dump(exclude_unset=True).items() if v is not None or k == "due_date"}
    for k, v in changes.items():
        setattr(t, k, v)
    log(db, user, t.id, "updated: " + ", ".join(changes))
    if not was_done and t.status == "Done" and t.recurrence != "none":
        db.add(Task(
            user_id=user.id, title=t.title, description=t.description, priority=t.priority,
            status="Todo", due_date=next_due(t.due_date, t.recurrence), category=t.category,
            tags=t.tags, recurrence=t.recurrence,
        ))
        log(db, user, t.id, "recurring copy created")
    db.commit()
    db.refresh(t)
    return out(t)


@router.delete("/tasks/{tid}", status_code=204)
def delete_task(tid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = own_task(db, user, tid)
    log(db, user, t.id, "deleted: " + t.title)
    db.delete(t)
    db.commit()


@router.post("/tasks/{tid}/subtasks", status_code=201)
def add_subtask(tid: int, d: SubIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = own_task(db, user, tid)
    db.add(Subtask(task_id=t.id, title=d.title))
    db.commit()
    db.refresh(t)
    return out(t)


@router.patch("/tasks/{tid}/subtasks/{sid}")
def toggle_subtask(tid: int, sid: int, d: SubPatch, db: Session = Depends(get_db), user: User = Depends(current_user)):
    t = own_task(db, user, tid)
    s = next((x for x in t.subtasks if x.id == sid), None)
    if not s:
        raise HTTPException(404, "Subtask not found")
    s.done = d.done
    db.commit()
    db.refresh(t)
    return out(t)


@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    ts = db.query(Task).filter(Task.user_id == user.id).all()
    total, done = len(ts), sum(t.status == "Done" for t in ts)
    return {
        "total": total, "completed": done, "pending": total - done,
        "overdue": sum(is_overdue(t) for t in ts),
        "completion_rate": round(100 * done / total) if total else 0,
        "by_priority": {p: sum(t.priority == p for t in ts) for p in ("Urgent", "High", "Medium", "Low")},
    }


@router.get("/export")
def export(format: str = "json", db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = [out(t) for t in db.query(Task).filter(Task.user_id == user.id).order_by(Task.id)]
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(COLS)
        w.writerows([[r[c] for c in COLS] for r in rows])
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=tasks.csv"})
    return Response(json.dumps(rows, indent=2), media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=tasks.json"})


@router.get("/activity")
def activity(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(ActivityLog).filter_by(user_id=user.id).order_by(ActivityLog.id.desc()).limit(50)
    return [{"task_id": r.task_id, "action": r.action, "at": r.created_at.isoformat()} for r in rows]
