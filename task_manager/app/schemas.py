"""Pydantic request schemas."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["Low", "Medium", "High", "Urgent"]
Status = Literal["Todo", "In Progress", "Done"]
Recur = Literal["none", "daily", "weekly", "monthly"]


class Cred(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=6, max_length=72)


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: Priority = "Medium"
    status: Status = "Todo"
    due_date: date | None = None
    category: str = Field("", max_length=50)
    tags: str = Field("", max_length=200)
    recurrence: Recur = "none"


class TaskPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    priority: Priority | None = None
    status: Status | None = None
    due_date: date | None = None
    category: str | None = Field(None, max_length=50)
    tags: str | None = Field(None, max_length=200)
    recurrence: Recur | None = None


class SubIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class SubPatch(BaseModel):
    done: bool
