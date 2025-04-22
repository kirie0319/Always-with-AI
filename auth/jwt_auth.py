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

from database import get_db
from models.users import User 

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_schema = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.utcnow() + expires_delta
  else: 
    expire = datetime.utcnow() + timedelta(minutes=15) 
  to_encode.update({"exp": expire})
  encode_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  return encode_jwt

async def get_current_user(token: str = Depends(oauth2_schema), db: AsyncSession = Depends(get_db)):
  print("\n--- get_current_user関数が呼び出されました ---")
  print(f"受け取ったトークン: {token}")
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="認証情報が無効です",
    headers={"WWW-Authenticate": "Bearer"},
  )
  try:
    print(f"SECRET_KEY: {SECRET_KEY[:3]}...")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"デコードされたペイロード: {payload}")
    username: str = payload.get("sub")
    if username is None:
      print("ペイロードに'sub'フィールドがありません")
      raise credentials_exception
    print(f"ユーザー名: {username}")
  except JWTError as e:
    print(f"JWTエラー: {str(e)}")
    raise credentials_exception
  stmt = select(User).where(User.username == username)
  result = await db.execute(stmt)
  user = result.scalar_one_or_none()

  if user is None:
    print(f"ユーザー '{username}' がデータベースに見つかりません")
    raise credentials_exception
  print(f"ユーザーが見つかりました: ID={user.id}, ユーザー名={user.username}")
  return user