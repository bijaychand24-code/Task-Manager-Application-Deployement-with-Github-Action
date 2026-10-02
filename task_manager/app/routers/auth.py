"""Register / login / logout endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..config import TOKEN_HOURS
from ..database import get_db
from ..models import User
from ..schemas import Cred
from ..security import hash_pw, make_token, verify_pw

router = APIRouter(prefix="/api")


@router.post("/register", status_code=201)
def register(c: Cred, db: Session = Depends(get_db)):
    email = c.email.strip().lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "Email already registered")
    db.add(User(email=email, password_hash=hash_pw(c.password)))
    db.commit()
    return {"ok": True}


@router.post("/login")
def login(c: Cred, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=c.email.strip().lower()).first()
    if not user or not verify_pw(c.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    response.set_cookie(
        "access_token", make_token(user.id), httponly=True,
        samesite="lax", max_age=TOKEN_HOURS * 3600,
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}
