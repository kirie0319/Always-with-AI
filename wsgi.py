# wsgi.py
from fastapi import FastAPI, Request, HTTPException, Depends, Response, BackgroundTasks, status, Form 
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json, uuid, traceback, os, anthropic, asyncio
from colorama import Fore, Style
from contextlib import asynccontextmanager
from openai import AsyncOpenAI
from typing import Dict, List, Any, Optional

# モジュールとクラスのインポート
from database import get_db, engine 
from models.users import User
from models.prompts import Prompt 
from auth.jwt_auth import (
  create_access_token,
  get_current_user,
  ACCESS_TOKEN_EXPIRE_MINUTES
)

# 新しいモジュールのインポート
from utils.file_operations import load_json, save_json, to_pretty_json, clear_cache
from utils.retry_logic import with_retry
from utils.ai_stream_client import AIStreamClient
from utils.chatroom_manager import ChatroomManager
from utils.openrouter_stream import AIOpenRouterStreamClient as OpenRouterStreamClient
from tasks import generate_summary_task

from api.financial_routes import router as financial_router

# 環境変数の読み込み
load_dotenv()

# 定数設定
DATA_DIR = "data"
MAX_RALLIES = 6
MAX_TOKENS_INPUT = 8_000
MAX_TOKENS_OUTPUT = 512
SAFETY_MARGIN = 500
OPENROUTER_MODELS = ["anthropic/claude-3.7-sonnet"]

# ディレクトリの作成
os.makedirs(DATA_DIR, exist_ok=True)

# APIクライアントの初期化
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")

anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=openrouter_api_key
)

# AIストリーミングクライアントの初期化
ai_stream_client = AIStreamClient(anthropic_client, openrouter_client)
openrouter_stream_client = OpenRouterStreamClient()

# チャットルームマネージャーの初期化
chatroom_manager = ChatroomManager(data_dir=DATA_DIR, max_rallies=MAX_RALLIES)

# データベース設定
DATABASE_URL = os.getenv("DATABASE_URL").replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# FastAPIアプリケーションの起動時・終了時の処理
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.execute(select(1))
            print("データベース接続成功")
    except Exception as e:
        print(f"データベース接続エラー: {e}")
    yield 
    print("アプリケーションシャットダウン")

# FastAPIアプリケーションの初期化
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("FLASK_SECRET_KEY")
)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(financial_router)

# データベース依存関数
async def get_db():
    async with async_session() as session:
        yield session

# ログイン・認証関連エンドポイント
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("auth/register.html", {"request": request})

@app.post("/register")
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


# login function here
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
    await chatroom_manager.get_or_create_chatroom(user.id)
    print(f"ユーザー {user.username}(ID: {user.id}) のチャットルームを確認/作成しました")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/validate-token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """トークンの検証用エンドポイント"""
    return {"valid": True, "username": current_user.username}

@app.get("/logout")
async def logout(request: Request):
    if "user_id" in request.session:
        del request.session["user_id"]
    if "username" in request.session:
        del request.session["username"]
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response

# メインアプリケーションエンドポイント
@app.get("/", response_class=HTMLResponse)
async def admin(request: Request, db: AsyncSession = Depends(get_db)):
    prompt_query = await db.execute(select(Prompt))
    available_prompts = prompt_query.scalars().all()
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin/admin.html", {"request": request, "available_prompts": available_prompts})

@app.get("/mobility", response_class=HTMLResponse)
async def mobility_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/mobility.html", {"request": request, "username": request.session.get("username")})

@app.get("/mobility/proposal", response_class=HTMLResponse)
async def proposal_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/proposal.html", {"request": request, "username": request.session.get("username")})

@app.get("/mobility/knowledge", response_class=HTMLResponse)
async def mobility_knowledge_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/knowledge.html", {"request": request, "username": request.session.get("username")})

@app.get("/financial", response_class=HTMLResponse)
async def financial_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("financial/financial.html", {"request": request, "username": request.session.get("username")})

@app.get("/conversation_history", response_class=HTMLResponse)
async def conversation_history(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    chatroom = await chatroom_manager.get_or_create_chatroom(user_id)
    history = await load_json(chatroom["files"]["chat_log"], [])
    return JSONResponse(content=history)

@app.post("/select_project")
async def select_project(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    prompt_id = data.get("prompt_id")
    project_id = data.get("project_id")
    print(f"Selected prompt ID: {prompt_id}")
    print(f"Selected project ID: {project_id}")

    if not prompt_id or not project_id:
        return JSONResponse(
            content={"success": False, "message": "プロンプトIDとプロジェクトIDが指定されていません"},
            status_code=400
        )
    request.session["selected_prompt_id"] = prompt_id
    redirect_url = f"/{project_id}"
    return JSONResponse(
        content={
            "success": True, 
            "redirect_url": redirect_url,
            "prompt_id": prompt_id,
            "project_id": project_id
            },
        status_code=200
    )

@app.get("/base", response_class=HTMLResponse)
async def base(request: Request):
    return templates.TemplateResponse("financial/index.html", {"request": request})
    

@app.post("/chat")
async def chat(
    request: Request, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = current_user.id
        
        # チャットデータの取得
        history, summary, user_history, thread_history = await chatroom_manager.get_chat_data(user_id)
        
        threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
        if summary and len(summary) > 0:
            summary_content = summary[0]["content"]
        else:
            summary_content = "" 
        last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
        
        # ユーザー入力の取得
        data = await request.json()
        user_input = data.get("message", "")
        print(f"User input: {user_input[:50]}...")
        try:
            user_type_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4.1",
                messages=[
                    {"role": "system", "content": f"""Classify the intention of the next utterance using a one-word label. Based on the recent conversation with users
        {threads}"""},
                    {"role": "user", "content": user_input} 
                ],
                max_tokens=4000,
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        try:
            user_content_response = await openrouter_client.chat.completions.create(
                model="openai/gpt-4.1",
                messages=[
                    {"role": "system", "content": f"""Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose. Based on the recent conversation with users
        {threads}"""},
                    {"role": "user", "content": user_input} 
                ],
                max_tokens=4000,
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        
        print("Type response:", user_type_response.choices[0].message.content)
        print("Content response:", user_content_response.choices[0].message.content)
        # ユーザーメッセージの追加
        user_message = {
            "role": "user", 
            "content": user_input, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        user_thread = {
            "role": "user", 
            "type": user_type_response.choices[0].message.content,
            "content": user_content_response.choices[0].message.content, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

        await chatroom_manager.add_message(user_id, user_message)
        await chatroom_manager.add_thread(user_id, user_thread)
        
        # 選択されたプロンプトの取得
        selected_prompt_id = request.session.get("selected_prompt_id")
        print(f"Selected prompt ID: {selected_prompt_id}")
        
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

        threads = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history]
        if summary and len(summary) > 0:
            summary_content = summary[0]["content"]
        else:
            summary_content = "" 
        last_conversation = [{"role": msg["role"], "content": msg["content"]} for msg in thread_history[-2:]]
        # システムプロンプトの構築
        system_prompt = f"""
        {base_prompt}

        ---
        ###Summary of conversation
        {summary_content}
        ###Recent conversation with users
        {threads}
        ###Last conversation with users
        {last_conversation}
        """
        print(system_prompt)
        async def generate():
            """ストリーミングレスポンスを生成する非同期ジェネレータ"""
            resp = ""
            try:
                # AIからのストリーミングレスポンスを取得
                async for text in openrouter_stream_client.stream_response(user_content_response.choices[0].message.content, system_prompt):
                    if isinstance(text, dict) and "error" in text:
                        yield f"data: {json.dumps(text)}\n\n"
                        return
                    resp += text
                    yield f"data: {json.dumps({'text': text})}\n\n"
                
                # アシスタントの応答を保存
                assistant_text = resp
                assistant_message = {
                    "role": "assistant", 
                    "content": assistant_text, 
                    "user_id": user_id,
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
                try:
                    assistant_type_response = await openrouter_client.chat.completions.create(
                        model="openai/gpt-4.1",
                        messages=[
                            {"role": "system", "content": "Classify the intention of the next utterance using a one-word label."},
                            {"role": "user", "content": assistant_text} 
                        ],
                        max_tokens=4000,
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                try:
                    assistant_content_response = await openrouter_client.chat.completions.create(
                        model="openai/gpt-4.1",
                        messages=[
                            {"role": "system", "content": "Summarize the main point of the following utterance in one sentence, clearly identifying the subject and purpose."},
                            {"role": "user", "content": assistant_text} 
                        ],
                        max_tokens=4000,
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                assistant_thread = {
                    "role": "assistant", 
                    "type": assistant_type_response.choices[0].message.content,
                    "content": assistant_content_response.choices[0].message.content, 
                    "user_id": user_id,
                    "id": str(uuid.uuid4()),
                    "timestamp": datetime.now().isoformat()
                }
                await chatroom_manager.add_message(user_id, assistant_message)
                await chatroom_manager.add_thread(user_id, assistant_thread)
                
                message_pair = {
                    "user": user_thread,
                    "assistant": assistant_thread,
                    "timestamp": datetime.now().isoformat()
                }
                await chatroom_manager.update_user_messages(user_id, message_pair)
                
                # 定期的にバックグラウンドでサマリーを更新
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

@app.post("/clear")
async def clear_chat_data(current_user: User = Depends(get_current_user)):
    """チャット履歴をクリアするエンドポイント"""
    user_id = current_user.id
    await chatroom_manager.clear_chat_data(user_id)
    return JSONResponse(content={"status": "success", "message": "Clear chat history"})

# 以下、プロンプト管理関連のエンドポイント（変更なし）
@app.get("/prompt", response_class=HTMLResponse)
async def get_prompts(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return templates.TemplateResponse("components/list.html", {
        "request": request,
        "data": prompts
    })

@app.get("/prompt/{prompt_id}", response_class=HTMLResponse)
async def get_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)

    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

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
    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

@app.delete("/prompt/{prompt_id}")
async def delete_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)
    
    await db.delete(prompt)
    await db.commit()
    
    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

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

    return templates.TemplateResponse("components/edit.html", {"request": request, "data": new_prompt})

@app.get("/select", response_class=HTMLResponse)
async def select_prompt_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return templates.TemplateResponse("components/select.html", {"request": request, "prompts": prompts})

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
    # port = int(os.environ.get('PORT', 5000))
    port = int(os.environ.get('PORT', 5001))
    uvicorn.run("wsgi:app", host="0.0.0.0", port=port, reload=True)