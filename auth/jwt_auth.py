# auth/jwt_auth.py
from datetime import datetime, timedelta
from typing import Optional 
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt 
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select 
import os
from pydantic import BaseModel

from database import get_db
from models.users import User 

SECRET_KEY = os.getenv("SECRET_KEY") or "always-ai-development-secret-key-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# リフレッシュトークンの有効期限（30日）
REFRESH_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_schema = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(BaseModel):
    username: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.utcnow() + expires_delta
  else: 
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  to_encode.update({"exp": expire})
  encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  return encode_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_tokens(data: dict):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data=data,
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data=data)
    tokens = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
    return tokens

async def get_current_user(token: str = Depends(oauth2_schema), db: AsyncSession = Depends(get_db)):
  
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="認証情報が無効です",
    headers={"WWW-Authenticate": "Bearer"},
  )
  
  if not token:
    print("Error: No token provided")
    raise credentials_exception
    
  try:
    if not SECRET_KEY:
      raise credentials_exception
      
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username: str = payload.get("sub")
    if username is None:
      print("Error: 'sub' field missing in paylßoad")
      raise credentials_exception
  except JWTError as e:
    print(f"JWT Error: {str(e)}")
    print(f"JWT Error type: {type(e)}")
    raise credentials_exception

  stmt = select(User).where(User.username == username)
  result = await db.execute(stmt)
  user = result.scalar_one_or_none()

  if user is None:
    print(f"Error: User '{username}' not found in database")
    raise credentials_exception
  return user

async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なリフレッシュトークンです"
            )
        return create_tokens(data={"sub": username})
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="リフレッシュトークンが無効です"
        )

async def authenticate_user(username: str, password: str, db: AsyncSession):
    """ユーザー認証を行う関数"""
    try:
        # ユーザー名またはメールアドレスでユーザーを検索
        stmt = select(User).where(
            (User.username == username) | (User.email == username)
        )
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None
        
        # パスワードの検証
        if not user.check_password(password):
            return None

        return user
    except Exception as e:
        print(f"認証エラー: {str(e)}")
        return None