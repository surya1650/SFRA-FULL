"""POST /api/auth/login + GET /api/auth/me + admin user-management endpoints.

The login endpoint accepts username + password (form-encoded, OAuth2-style)
and returns a JWT bearer token. ``/me`` returns the current user. Admin
endpoints under ``/api/users/*`` create / list users — gated on the ADMIN
role via ``require_admin``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Use a permissive email validator: built-in EmailStr rejects RFC-2606
# reserved TLDs like ``.test`` which we use in tests. We still enforce
# the structural shape (one ``@``, non-empty local + domain).
def _validate_email_shape(v: str) -> str:
    if not isinstance(v, str) or v.count("@") != 1:
        raise ValueError("invalid email address")
    local, _, domain = v.partition("@")
    if not local or not domain or "." not in domain:
        raise ValueError("invalid email address")
    return v
from sqlalchemy import select
from sqlalchemy.orm import Session

from sfra_full.audit import AuditAction, record_event
from sfra_full.api.deps import get_session
from sfra_full.auth import (
    Role,
    User,
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)


router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role
    user_id: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    full_name: Optional[str]
    role: Role
    is_active: bool
    last_login_at: Optional[datetime]


class UserCreate(BaseModel):
    email: str
    full_name: Optional[str] = None
    password: str = Field(min_length=8)
    role: Role = Role.ENGINEER

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        return _validate_email_shape(v)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/api/auth/login", response_model=TokenResponse)
def login(
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
) -> TokenResponse:
    user = session.scalar(select(User).where(User.email == username))
    if user is None or not user.is_active:
        record_event(
            session,
            action=AuditAction.LOGIN_FAILED,
            actor_email=username,
            request_method="POST",
            request_path="/api/auth/login",
            response_status=401,
            detail={"reason": "user_not_found_or_inactive"},
            commit=True,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not verify_password(password, user.hashed_password):
        record_event(
            session,
            action=AuditAction.LOGIN_FAILED,
            actor_id=user.id,
            actor_email=user.email,
            actor_role=user.role.value,
            request_method="POST",
            request_path="/api/auth/login",
            response_status=401,
            detail={"reason": "bad_password"},
            commit=True,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    record_event(
        session,
        action=AuditAction.LOGIN,
        actor_id=user.id,
        actor_email=user.email,
        actor_role=user.role.value,
        request_method="POST",
        request_path="/api/auth/login",
        response_status=200,
    )
    session.commit()

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        role=user.role,
        user_id=user.id,
    )


@router.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post(
    "/api/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    session: Session = Depends(get_session),
    actor: User = Depends(require_admin),
) -> User:
    existing = session.scalar(select(User).where(User.email == payload.email))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already in use")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    session.add(user)
    session.flush()
    record_event(
        session,
        action=AuditAction.USER_CREATE,
        actor_id=actor.id,
        actor_email=actor.email,
        actor_role=actor.role.value,
        target_kind="user",
        target_id=user.id,
        request_method="POST",
        request_path="/api/users",
        response_status=201,
        detail={"created_email": user.email, "created_role": user.role.value},
    )
    session.commit()
    session.refresh(user)
    return user


@router.get(
    "/api/users",
    response_model=list[UserOut],
    dependencies=[Depends(require_admin)],
)
def list_users(session: Session = Depends(get_session)) -> list[User]:
    return list(session.scalars(select(User).order_by(User.created_at.desc())))
