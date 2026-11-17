from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_user_optional,
)
from app.models.user import User, Organization
from app.models.repository import Repository

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    github_id: Optional[str] = None
    avatar_url: Optional[str] = None
    organization_id: int
    organization_name: str
    organization_slug: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates user credentials and returns a secure JWT access token.
    Never exposes passwords, salts, or internal hashes in the response.
    """
    stmt = select(User).where(User.username == payload.username.strip(), User.is_active == True)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.salt, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    # Fetch organization
    org = await db.get(Organization, user.organization_id)
    org_name = org.name if org else "Default Organization"
    org_slug = org.slug if org else "default"

    token = create_access_token(user)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            github_id=user.github_id,
            avatar_url=user.avatar_url,
            organization_id=user.organization_id,
            organization_name=org_name,
            organization_slug=org_slug
        )
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns the currently authenticated user profile."""
    org = await db.get(Organization, user.organization_id)
    org_name = org.name if org else "Default Organization"
    org_slug = org.slug if org else "default"

    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        github_id=user.github_id,
        avatar_url=user.avatar_url,
        organization_id=user.organization_id,
        organization_name=org_name,
        organization_slug=org_slug
    )
