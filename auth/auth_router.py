# auth/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from .jwt_auth import authenticate_user, create_tokens, refresh_token
from pydantic import BaseModel
from models.users import User
from sqlalchemy.future import select

router = APIRouter()

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh-token")
async def refresh_access_token(request: RefreshTokenRequest):
    return await refresh_token(request.refresh_token)

@router.post("/token")
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(
        (User.username == form_data.username) | (User.email == form_data.username)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.check_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # セッションにユーザー情報を保存
    request.session["user_id"] = user.id
    request.session["username"] = user.username

    # トークンの作成 - ユーザー名を使用
    tokens = create_tokens({"sub": user.username})
    
    return tokens