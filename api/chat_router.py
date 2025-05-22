# api/chat_router.py
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from models.users import User
from auth.jwt_auth import get_current_user
from utils.chatroom_manager import ChatroomManager
from utils.openrouter_stream import AIOpenRouterStreamClient as OpenRouterStreamClient
from utils.file_operations import load_json, to_pretty_json
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from tasks import generate_summary_task
import json, uuid, traceback
from datetime import datetime
DATA_DIR = "data"
MAX_RALLIES = 6

chatroom_manager = ChatroomManager(data_dir=DATA_DIR, max_rallies=MAX_RALLIES)
openrouter_stream_client = OpenRouterStreamClient()

router = APIRouter()

@router.get("/conversation_history", response_class=HTMLResponse)
async def conversation_history(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    user_id = current_user.id
    chatroom = await chatroom_manager.get_or_create_chatroom(user_id)
    history = await load_json(chatroom["files"]["chat_log"], [])
    return JSONResponse(content=history)

@router.post("/clear")
async def clear_chat_data(current_user: User = Depends(get_current_user)):
    """チャット履歴をクリアするエンドポイント"""
    user_id = current_user.id
    await chatroom_manager.clear_chat_data(user_id)
    return JSONResponse(content={"status": "success", "message": "Clear chat history"})

@router.post("/message_chat")
async def message_chat(
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
            user_type_response = await openrouter_stream_client.type_response(
                user_input,
                threads,
                model="openai/gpt-4.1",
                max_tokens=4000
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        try:
            user_content_response = await openrouter_stream_client.content_response(
                user_input,
                threads,
                model="openai/gpt-4.1",
                max_tokens=4000
            )
        except Exception as e:
            print(f"Error: {e}")
            return JSONResponse(content={"error": str(e)}, status_code=500)
        
        print("Type response:", user_type_response)
        print("Content response:", user_content_response)
        # ユーザーメッセージの追加
        user_message = {
            "role": "user", 
            "content": user_input, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        user_thread = {
            "role": "user", 
            "type": user_type_response,
            "content": user_content_response, 
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }

        await chatroom_manager.add_message(user_id, user_message)
        await chatroom_manager.add_thread(user_id, user_thread)
        
        base_prompt = """
        You are a helpful AI assistant. Respond to user queries clearly and concisely.

        Instructions:
        - Be direct and helpful
        - Keep responses focused on the user's question
        - If you don't know something, say so
        - Ask for clarification if the request is unclear
        - Respond in the only same language as the user's question

        """
        
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
                async for text in openrouter_stream_client.stream_response(user_content_response, system_prompt):
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
                    assistant_type_response = await openrouter_stream_client.type_response(
                        assistant_text,
                        threads,
                        model="openai/gpt-4.1",
                        max_tokens=4000
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                try:
                    assistant_content_response = await openrouter_stream_client.content_response(
                        assistant_text,
                        threads,
                        model="openai/gpt-4.1",
                        max_tokens=4000
                    )
                except Exception as e:
                    print(f"Error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                assistant_thread = {
                    "role": "assistant", 
                    "type": assistant_type_response,
                    "content": assistant_content_response, 
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
