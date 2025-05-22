# auth/auth_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from .jwt_auth import authenticate_user, create_tokens, refresh_token
from pydantic import BaseModel
from models.users import User
from sqlalchemy.future import select
from auth.jwt_auth import (
  create_access_token,
  get_current_user,
  ACCESS_TOKEN_EXPIRE_MINUTES
)
from utils.chatroom_manager import ChatroomManager
import os

DATA_DIR = "data"
MAX_RALLIES = 6

os.makedirs(DATA_DIR, exist_ok=True)

chatroom_manager = ChatroomManager(data_dir=DATA_DIR, max_rallies=MAX_RALLIES)
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

@router.get("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """トークンの検証用エンドポイント"""
    return {"valid": True, "username": current_user.username}

@router.post("/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # メールアドレスの重複チェック
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="このメールアドレスはすでに登録されています"
            )
        
        # ユーザー名の重複チェック
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="このusernameはすでに登録されています"
            )
        
        # 新規ユーザーの作成
        new_user = User(
            username=username,
            email=email
        )
        new_user.set_password(password)

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # ユーザー登録後、チャットルームを作成
        await chatroom_manager.get_or_create_chatroom(new_user.id)
        print(f"新規ユーザー {username}(ID: {new_user.id}) のチャットルームを作成しました")

        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException as e:
        # 既存のHTTPExceptionを再送信
        raise e
    except Exception as e:
        print(f"ユーザー登録エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"ユーザー登録中にエラーが発生しました: {str(e)}"
        )
    
@router.get("/logout")
async def logout(request: Request):
    if "user_id" in request.session:
        del request.session["user_id"]
    if "username" in request.session:
        del request.session["username"]
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response