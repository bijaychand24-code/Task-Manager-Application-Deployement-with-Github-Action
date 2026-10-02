"""FastAPI entrypoint: run with `uvicorn app.main:app --reload`."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from .database import Base, engine
from .routers import auth, tasks

Base.metadata.create_all(engine)
app = FastAPI(title="Task Manager")
app.include_router(auth.router)
app.include_router(tasks.router)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/")
def index(request: Request):
    if not request.cookies.get("access_token"):
        return RedirectResponse("/login")
    return templates.TemplateResponse(request, "index.html")


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")
