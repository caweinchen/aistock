from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import User, get_db
from app.routers.auth import get_admin_user
from app.schemas import UpdateUserRequest, UserResponse

router = APIRouter(prefix="/api/admin")

@router.get("/users", response_model=list[UserResponse])
def list_users(_admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, request: UpdateUserRequest, admin: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == admin.id:
        if request.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot disable yourself")
        if request.role is not None and request.role != "admin":
            raise HTTPException(status_code=400, detail="Cannot remove your own admin role")

    if request.role is not None:
        if request.role not in {"admin", "user"}:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = request.role

    if request.is_active is not None:
        user.is_active = request.is_active

    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user
