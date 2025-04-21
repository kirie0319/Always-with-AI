# wsgi.py
from fastapi import FastAPI, Request, HTTPException, Depends, Response, BackgroundTasks, status, Form 
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles 
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json, uuid, threading, yaml, traceback, sys, time, config, os, anthropic, aiofiles, asyncio
from colorama import Fore, Style, init 
from tasks import generate_summary_task
from contextlib import asynccontextmanager
from openai import OpenAI
from database import get_db, engine 
from models.users import User
from models.prompts import Prompt 
from auth.jwt_auth import (
  create_access_token,
  get_current_user,
  ACCESS_TOKEN_EXPIRE_MINUTES
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

load_dotenv()

MAX_RALLIES = 6
YAML_PATH = "prompts/specific/finance.yaml"
MAX_TOKENS_INPUT  = 8_000   # Claude に渡す入力上限
MAX_TOKENS_OUTPUT = 512     # 期待する出力上限
SAFETY_MARGIN     = 500     # header 系を見込んだ余白
OPENROUTER_MODELS = [
  "anthropic/claude-3.7-sonnet"
]

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

anthropic_client = anthropic.Anthropic(
  api_key=anthropic_api_key,
)

openrouter_client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=openrouter_api_key
)

@asynccontextmanager
async def lifespan(app: FastAPI):
  try:
    async with engine.begin() as conn:
      await conn.execute(select(1))
      print("データベース接続成功")
  except Exception as e:
    print(f"データベース接続エラー: {e}")
  yield 
  print("アプリケーションショットダウン")

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("FLASK_SECRET_KEY")
)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Data base setting
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
  async with async_session() as session:
    yield session

async def load_json(filepath, default):
  try:
    async with aiofiles.open(filepath, "r", encoding='utf-8') as f:
      content = await f.read()
      return json.loads(content)
  except (FileNotFoundError, json.JSONDecodeError):
    return default

async def save_json(filepath, data):
  async with aiofiles.open(filepath, "w", encoding='utf-8') as f:
    await f.write(json.dumps(data, indent=2, ensure_ascii=False))

async def to_pretty_json(data):
  return json.dumps(data, ensure_ascii=False, indent=2)

async def get_user_id(user_identifier):
  user_history = await load_json(config.USER_HISTORY_FILE, {})

  if user_identifier is None or isinstance(user_history, list):
    user_history = {}

  if user_identifier not in user_history:
    user_history[user_identifier] = {
      "user_id": str(uuid.uuid4()),
      "created_at": datetime.now().isoformat(),
      "messages": []
    }
    await save_json(config.USER_HISTORY_FILE, user_history)

  return user_history[user_identifier]["user_id"]

# async def update_user_messages(user_identifier, message_pair):
#   user_history = await load_json(config.USER_HISTORY_FILE, {})
#   history = await load_json(config.CHAT_LOG_FILE, [])

#   if user_history is None or isinstance(user_history, list):
#     user_history = {}

#   if user_identifier not in user_history:
#     await get_user_id(user_identifier)
#     user_history = await load_json(config.USER_HISTORY_FILE, {})

#     if user_history is None or isinstance(user_history, list):
#       user_history = {}
#       user_history[user_identifier] = {
#         "user_id": str(uuid.uuid4()),
#         "created_at": datetime.now().isoformat(),
#         "messages": []
#       }
#   if "messages" not in user_history[user_identifier]:
#     user_history[user_identifier]["messages"] = []

#   if len(history) > 2:
#     user_history[user_identifier]["messages"].append(history[-4:-2])

#   if len(user_history[user_identifier]["messages"]) > MAX_RALLIES:
#     user_history[user_identifier]["messages"] = user_history[user_identifier]["messages"][-MAX_RALLIES:]

#   await save_json(config.USER_HISTORY_FILE, user_history)

async def get_user_files(user_id):
  return {
    "chat_log": f"data/chat_log_{user_id}.json",
    "summary": f"data/summary_{user_id}.json",
    "user_history": f"data/user_history_{user_id}.json"
  }

CHATROOM_FILE = "data/chatroom.json"

async def get_or_create_chatroom(user_id):
  chatrooms = await load_json(CHATROOM_FILE, {})

  if user_id not in chatrooms:
    user_files = await get_user_files(user_id)
    await save_json(user_files["chat_log"], [])
    await save_json(user_files["summary"], [])
    await save_json(user_files["user_history"], {})

    chatrooms[user_id] = {
      "created_ai": datetime.now().isoformat(),
      "files": user_files
    }
    await save_json(CHATROOM_FILE, chatrooms)
  return chatrooms[user_id]

async def get_last_conversation_pair(user_id):
  chatroom = await get_or_create_chatroom(user_id)
  history = await load_json(chatroom["files"]["chat_log"], [])
  if len(history) < 2:
    return None
  for i in range(len(history) - 2, -1, -1):
    if history[i]["role"] == "user" and history[i + 1]["role"] == "assistant":
      return {
        "user": history[i],
        "assistant": history[i + 1]
      }
  return None 

async def update_user_messages(user_id, message_pair):
  chatroom = await get_or_create_chatroom(user_id)
  user_history = await load_json(chatroom["files"]["user_history"], {})
  history = await load_json(chatroom["files"]["chat_log"], [])

  if user_id not in user_history:
    user_history[user_id] = {
      "created_at": datetime.now().isoformat(),
      "messages": []
    }
  if "messages" not in user_history[user_id]:
    user_history[user_id]["messages"] = []
  if len(history) > 2:
    user_history[user_id]["messages"].append(history[-4:-2])
  if len(user_history[user_id]["messages"]) > MAX_RALLIES:
    user_history[user_id]["messages"] = user_history[user_id]["messages"][-MAX_RALLIES:]
  await save_json(chatroom["files"]["user_history"], user_history)

async def stream_anthropic_response(user_input, system_prompt):
  max_retries = 5
  retry_count = 0
  backoff_time = 1
  while retry_count < max_retries:
    try:
      with anthropic_client.messages.stream(
        model="claude-3-7-sonnet-20250219",
        max_tokens=4000,
        system=system_prompt,
        messages=[
          {"role": "user", "content": user_input}
        ]
      ) as stream:
          assistant_response = ""
          for text in stream.text_stream:
            print(text, end="", flush=True)
            assistant_response += text 
            yield text 
          break
    except anthropic.APIStatusError as e:
      if hasattr(e, '_status_code') and e._status_code == 429 or 'overloaded_error' in str(e):
        retry_count += 1
        if retry_count < max_retries:
          print(f"\n{Fore.YELLOW}APIが混雑しています。{backoff_time}秒後に再試行します...{Style.RESET_ALL}")
          await asyncio.sleep(backoff_time)
          backoff_time *= 2
          print(f"\n{Fore.BLUE}Claude: {Style.RESET_ALL}", end="")
        else:
          print(f"\n{Fore.RED}APIが混雑しているため、リクエストを完了できませんでした。しばらく時間をおいてお試しください。{Style.RESET_ALL}\n")
          yield json.dumps({"error": "APIが混雑しています。時間をおいて再度お試しください。"})
      else:
        print(f"\n{Fore.RED}エラーが発生しました: {e}{Style.RESET_ALL}\n")
        yield json.dumps({"error": str(e)})
        break

async def stream_openrouter_response(user_input, system_prompt):
  max_retries = 5
  retry_count = 0
  backoff_time = 1
  while retry_count < max_retries:
    try:
      stream = openrouter_client.chat.completions.create(
        model="anthropic/claude-3.7-sonnet",
        messages=[
          {"role": "system", "content": system_prompt},
          {"role": "user", "content": user_input} 
        ],
        max_tokens=4000,
        stream=True
      )

      assistant_response = ""
      print(f"\n{Fore.BLUE}Claude:{Style.RESET_ALL}", end="")

      async for chunk in stream:
        delta = chunk.choices[0].delta 
        if delta and delta.content:
          print(delta.content, end="", flush=True)
          assistant_response += delta.content 
          yield delta.content
      break 
    except Exception as e:
      if "429" in str(e).lower() or "overload" in str(e).lower():
        retry_count += 1
        if retry_count < max_retries:
          print(f"\n{Fore.YELLOW}APIが混雑しています。{backoff_time}秒後に再試行します...{Style.RESET_ALL}")
          await asyncio.sleep(backoff_time)
          backoff_time *= 2
          print(f"\n{Fore.BLUE}Claude:{Style.RESET_ALL} ", end="")
        else:
          print(f"\n{Fore.RED}APIが混雑しているため、リクエストを完了できませんでした。{Style.RESET_ALL}\n")
          yield json.dumps({"error": "APIが混雑しています。時間をおいて再度お試しください。"})
      else:
        print(f"\n{Fore.RED}エラーが発生しました: {e}{Style.RESET_ALL}\n")
        yield json.dumps({"error": str(e)})
        break

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
  return templates.TemplateResponse("login.html", {"request": request})

# @app.get(
#   "/register", response_class=HTMLResponse)
# async def register_page(
#   request: Request
# ):
#   return templates.TemplateResponse("register.html", {"request": request})
@app.post("/register")
async def register_user(
  username: str = Form(...),
  email: str = Form(...),
  password: str = Form(...),
  db: AsyncSession = Depends(get_db)
):
  stmt = select(User).where(User.email == email)
  result = await db.execute(stmt)
  if result.scalar_one_or_none():
    raise HTTPException(
      status_code=400,
      detail="このメールアドレスはすでに登録されています"
    )
  stmt = select(User).where(User.username == username)
  result = await db.execute(stmt)
  if result.scalar_one_or_none():
    raise HTTPException(
      status_code=400,
      detail="このusernameはすでに登録されています"
    )
  new_user = User(
    username=username,
    email=email
  )
  new_user.set_password(password)

  db.add(new_user)
  await db.commit()
  await db.refresh(new_user)
  
  # ユーザー登録後、チャットルームを作成
  await get_or_create_chatroom(new_user.id)
  print(f"新規ユーザー {username}(ID: {new_user.id}) のチャットルームを作成しました")

  return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

# @app.post("/token")
# async def login_for_access_token(
#   request: Request,
#   form_data: OAuth2PasswordRequestForm = Depends(),
#   db: AsyncSession = Depends(get_db)
# ):

#   stmt = select(User).where(
#     (User.username == form_data.username) | (User.email == form_data.username)
#   )
#   result = await db.execute(stmt)
#   user = result.scalar_one_or_none()

#   if not user or not user.check_password(form_data.password):
#     raise HTTPException(
#       status_code=status.HTTP_401_UNAUTHORIZED,
#       detail="ユーザー名またはパスワードが正しくありません",
#       headers={"WWW-Authenticate": "Bearer"},
#     )
#   request.session["user_id"] = user.id
#   request.session["username"] = user.username

#   access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#   access_token = create_access_token(
#     data={"sub": user.username},
#     expires_delta=access_token_expires
#   )
#   return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token")
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

  # ログイン時にチャットルームを確認/作成
  await get_or_create_chatroom(user.id)
  print(f"ユーザー {user.username}(ID: {user.id}) のチャットルームを確認/作成しました")

  access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  access_token = create_access_token(
    data={"sub": user.username},
    expires_delta=access_token_expires
  )
  return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register")
async def register_user(
  username: str = Form(...),
  email: str = Form(...),
  password: str = Form(...),
  db: AsyncSession = Depends(get_db)
):
  stmt = select(User).where(User.email == email)
  result = await db.execute(stmt)
  if result.scalar_one_or_none():
    raise HTTPException(
      status_code=400,
      detail="このメールアドレスはすでに登録されています"
    )
  stmt = select(User).where(User.username == username)
  result = await db.execute(stmt)
  if result.scalar_one_or_none():
    raise HTTPException(
      status_code=400,
      detail="このusernameはすでに登録されています"
    )
  new_user = User(
    username=username,
    email=email
  )
  new_user.set_password(password)

  db.add(new_user)
  await db.commit()

  return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """トークンの検証用エンドポイント"""
    return {"valid": True, "username": current_user.username}

@app.get("/", response_class=HTMLResponse)
async def index(
  request: Request,
):
  user_id = request.session.get("user_id")
  if not user_id:
    return RedirectResponse(url="/login", status_code=302)
  return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(
  request: Request, 
  background_tasks: BackgroundTasks,
  current_user: User = Depends(get_current_user), 
  db: AsyncSession = Depends(get_db)
  ):
  max_retries = 5
  retry_count = 0
  backoff_time = 1
  try:
    user_id = current_user.id 
    chatroom = await get_or_create_chatroom(user_id)
    user_files = chatroom["files"]
    last_pair = await get_last_conversation_pair(user_id)
    if last_pair:
      last_two_json = json.dumps(last_pair, ensure_ascii=False, indent=2)
    else:
      last_two_json = "会話履歴が見つかりませんでした。"
    history = await load_json(user_files["chat_log"], [])
    history_json = await to_pretty_json(history)

    summary = await load_json(user_files["summary"], [])
    summary_json = await to_pretty_json(summary)

    user_history = await load_json(user_files["user_history"], {})
    user_history_json = await to_pretty_json(user_history)

    data = await request.json()
    user_input = data.get("message", "")
    print(f"User input: {user_input[:50]}...")

    user_message = {
        "role": "user", 
        "content": user_input, 
        "user_id": user_id,
        "timestamp": datetime.now().isoformat()
    }
    history.append(user_message)
    await save_json(user_files["chat_log"], history)

    selected_prompt_id = request.session.get("selected_prompt_id")
    print(selected_prompt_id)
    base_prompt = "you are helpful AI assistant"
    if selected_prompt_id:
      stmt = select(Prompt).where(Prompt.id == int(selected_prompt_id))
      result = await db.execute(stmt)
      prompt_obj = result.scalar_one_or_none()
      if prompt_obj:
        print(f"Found prompt: {prompt_obj.name}")
        base_prompt = prompt_obj.content
      else:
        print("Prompt object not found for ID:", selected_prompt_id) 
      print("Calling Anthropic API...")
      prompt = f"""
      {base_prompt}

      ---
      ###Summary fo conversation
      {summary_json}
      ###Recent conversation with users
      {user_history_json}
      ###Last conversation with users
      {last_two_json}
      """


      async def generate():
        resp = ""
        retry_count = 0
        backoff_time = 1
        try:
          async for text in stream_anthropic_response(user_input, prompt):
            print(prompt)
            if isinstance(text, dict) and "error" in text:
              yield f"data: {json.dumps(text)}\n\n"
              return
            resp += text
            yield f"data: {json.dumps({'text': text})}\n\n"
          assistant_text = resp
            
          assistant_message = {
            "role": "assistant", 
            "content": assistant_text, 
            "user_id": user_id,
            "id": str(uuid.uuid4()),  # Adding message ID like in the second code
            "timestamp": datetime.now().isoformat()
          }
          history.append(assistant_message)
          await save_json(user_files["chat_log"], history)

          try:
            summarize_result = await asyncio.to_thread(
              anthropic_client.messages.create,
              model="claude-3-haiku-20240307",
              max_tokens=2048,
              system="""You are an expert conversation summarizer.

              Your task is to analyze and summarize response of AI assistant. The goal is to extract key details and provide a clear, short, structured summary of the conversation.

              Use the following output format:

              ---

              ### Chat Summary

              #### 1. **Overview**
              Briefly describe the overall context of the conversation, the participants, and the tone.

              #### 2. **Key Points**
              List 5-7 bullet points that highlight the most important facts, insights, or decisions discussed during the conversation.

              #### 3. **Topic Timeline** (optional)
              If applicable, outline the main topics discussed in chronological order.

              #### 4. **Follow-up Items**
              List any remaining questions, action items, or topics that could be explored further.

              #### 5. **Context Notes**
              Mention any relevant background, such as the fictional setting, tone of the assistant, or relationship between participants.

              ---
              """,
              messages=[
                {"role": "user", "content": assistant_text}
              ]
            )
            assistant_summary_message = {
              "role": "assistant",
              "content": summarize_result.content[0].text,
              "user_id": user_id,
              "id": str(uuid.uuid4()),
              "timestamp": datetime.now().isoformat()
            }
            message_pair = {
              "user": user_message,
              "assistant": assistant_summary_message,
              "timestamp": datetime.now().isoformat()
            }
            await update_user_messages(user_id, message_pair)
          except Exception as e:
            print(f"Error generating summary: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

          if len(history) % 7 == 0:
            background_tasks.add_task(
              generate_summary_task, 
              await to_pretty_json(history),
              user_id
            )
        except Exception as e:
          yield f"data: {json.dumps({'error': str(e)})}\n\n"
          error_details = traceback.format_exc()
          print(f"Error in chat: {str(e)}\n{error_details}")
      return StreamingResponse(generate(), media_type="text/event-stream")
  except Exception as e:
    error_details = traceback.format_exc()
    print(f"Error in chat: {str(e)}\n{error_details}")
    return JSONResponse(
      content={"error": str(e), "details": error_details},
      status_code=500
    )

@app.get("/debug/token")
async def debug_token(request: Request):
    """トークンデバッグ用エンドポイント"""
    auth_header = request.headers.get("Authorization")
    
    result = {
        "auth_header_exists": auth_header is not None,
        "auth_header": auth_header[:20] + "..." if auth_header else None,
    }
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            result["token_valid"] = True
            result["payload"] = payload
        except Exception as e:
            result["token_valid"] = False
            result["error"] = str(e)
    
    return JSONResponse(content=result)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """リクエストヘッダーをログに記録するミドルウェア"""
    print(f"\n受信したリクエスト: {request.method} {request.url.path}")
    print("認証ヘッダー:", request.headers.get("Authorization"))
    
    response = await call_next(request)
    
    print(f"レスポンスステータス: {response.status_code}")
    return response


@app.post("/clear")
async def clear_chat_data(current_user: User = Depends(get_current_user)):
  user_id = current_user.id 
  chatroom = await get_or_create_chatroom(user_id)
  user_files = chatroom["files"]
  await save_json(user_files["chat_log"], [])
  await save_json(user_files["summary"], [])
  await save_json(user_files["user_history"], {})
  return JSONResponse(content={"status": "success", "message": "Clear chat history"})

@app.get("/prompt", response_class=HTMLResponse)
async def get_prompts(request: Request, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Prompt))
  prompts = result.scalars().all()
  return templates.TemplateResponse("list.html", {
    "request": request,
    "data": prompts
  })

@app.get("/prompt/{prompt_id}", response_class=HTMLResponse)
async def get_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
  result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
  prompt = result.scalar_one_or_none()

  if not prompt:
    return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)

  return templates.TemplateResponse("edit.html", {"request": request, "data": prompt})

@app.patch("/prompt/{prompt_id}")
async def update_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)
    
    p_data = await request.json()
    if "content" in p_data:
        prompt.content = p_data["content"]

    await db.commit()
    return templates.TemplateResponse("edit.html", {"request": request, "data": prompt})

@app.delete("/prompt/{prompt_id}")
async def delete_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)
    
    await db.delete(prompt)
    await db.commit()
    
    return templates.TemplateResponse("edit.html", {"request": request, "data": prompt})

@app.post("/prompts/create")
async def create_prompt(request: Request, db: AsyncSession = Depends(get_db)):
    p_data = await request.json()

    if not p_data or "content" not in p_data or not isinstance(p_data["content"], str):
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプト情報が不足しています"}, status_code=400)

    new_prompt = Prompt(
        name=p_data["name"],
        content=p_data["content"],
        description=p_data["description"]    
    )
    
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)

    return templates.TemplateResponse("edit.html", {"request": request, "data": new_prompt})

@app.get("/select", response_class=HTMLResponse)
async def select_prompt_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return templates.TemplateResponse("select.html", {"request": request, "prompts": prompts})

@app.get("/api/prompt/{prompt_id}")
async def get_prompt_api(prompt_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return JSONResponse(
            content={"error": "プロンプトが見つかりません"},
            status_code=404
        )
    
    return JSONResponse(content={
        "id": prompt.id,
        "name": prompt.name,
        "description": prompt.description,
        "content": prompt.content
    })

@app.post("/api/select-prompt")
async def select_prompt_api(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    prompt_id = data.get("prompt_id")

    if not prompt_id:
        return JSONResponse(
            content={"success": False, "message": "プロンプトIDが指定されていません"},
            status_code=400
        )

    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        return JSONResponse(
            content={"success": False, "message": "プロンプトが見つかりません"},
            status_code=404
        )

    print(f"selected_prompt_idを{prompt_id}に設定します")
    request.session["selected_prompt_id"] = prompt_id
    request.session["selected_prompt_name"] = prompt.name

    return JSONResponse(content={
        "success": True,
        "prompt_id": prompt_id,
        "prompt_name": prompt.name 
    })

if __name__ == '__main__':
    import uvicorn
    # port = int(os.environ.get('PORT', 5001))
    port = int(os.environ.get('PORT', 5000))
    uvicorn.run("wsgi:app", host="0.0.0.0", port=port, reload=True)