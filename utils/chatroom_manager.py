# utils/chatroom_manager.py
import uuid
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 前述の最適化されたファイル操作関数をインポート
from .file_operations import load_json, save_json, to_pretty_json

class ChatroomManager:
    """チャットルームとユーザーデータの管理を行うクラス"""
    
    def __init__(self, data_dir: str = "data", max_rallies: int = 6):
        self.data_dir = data_dir
        self.max_rallies = max_rallies
        self.chatroom_file = os.path.join(data_dir, "chatroom.json")
        
        # ディレクトリが存在することを確認
        os.makedirs(data_dir, exist_ok=True)
    
    async def get_user_files(self, user_id: str) -> Dict[str, str]:
        """ユーザーに関連するファイルパスを取得"""
        return {
            "chat_log": os.path.join(self.data_dir, f"chat_log_{user_id}.json"),
            "summary": os.path.join(self.data_dir, f"summary_{user_id}.json"),
            "user_history": os.path.join(self.data_dir, f"user_history_{user_id}.json"),
            "thread_history": os.path.join(self.data_dir, f"thread_history_{user_id}.json"),
            "strategy_data": os.path.join(self.data_dir, f"strategy_{user_id}.json")
        }
    
    async def get_or_create_chatroom(self, user_id: str) -> Dict[str, Any]:
        chatrooms = await load_json(self.chatroom_file, {})
        if user_id not in chatrooms:
            chatrooms[user_id] = {
                "created_at": datetime.now().isoformat(),
                "files": await self.get_user_files(user_id)
            }
            await save_json(self.chatroom_file, chatrooms)
        user_files = await self.get_user_files(user_id)
        required_files = {
            "chat_log": [],
            "summary": [],
            "user_history": {},
            "thread_history": [],
            "strategy_data": {}
        }
        for file_key, default_value in required_files.items():
            file_path = user_files[file_key]
            if not os.path.exists(file_path):
                await save_json(file_path, default_value)
        chatrooms[user_id]["files"] = user_files
        return chatrooms[user_id]
    
    async def get_last_conversation_pair(self, user_id: str) -> Optional[Dict[str, Dict]]:
        """最新の会話ペア（ユーザー・アシスタント）を取得"""
        chatroom = await self.get_or_create_chatroom(user_id)
        # change the caht_log to thread_history
        history = await load_json(chatroom["files"]["thread_history"], [])
        
        if len(history) < 2:
            return None
            
        for i in range(len(history) - 2, -1, -1):
            if history[i]["role"] == "user" and history[i + 1]["role"] == "assistant":
                return {
                    "user": history[i],
                    "assistant": history[i + 1]
                }
                
        return None
    
    async def update_user_messages(self, user_id: str, message_pair: Dict[str, Any]) -> None:
        """ユーザーのメッセージ履歴を更新"""
        chatroom = await self.get_or_create_chatroom(user_id)
        user_history = await load_json(chatroom["files"]["user_history"], {})
        # change the chat_log to thread_history
        history = await load_json(chatroom["files"]["thread_history"], [])
        
        if user_id not in user_history:
            user_history[user_id] = {
                "created_at": datetime.now().isoformat(),
                "messages": []
            }
            
        if "messages" not in user_history[user_id]:
            user_history[user_id]["messages"] = []
            
        if len(history) > 2:
            user_history[user_id]["messages"].append(history[-4:-2])
            
        if len(user_history[user_id]["messages"]) > self.max_rallies:
            user_history[user_id]["messages"] = user_history[user_id]["messages"][-self.max_rallies:]
            
        await save_json(chatroom["files"]["user_history"], user_history)
    
    async def add_message(self, user_id: str, message: Dict[str, Any]) -> None:
        """メッセージをチャット履歴に追加"""
        chatroom = await self.get_or_create_chatroom(user_id)
        history = await load_json(chatroom["files"]["chat_log"], [])
        history.append(message)
        await save_json(chatroom["files"]["chat_log"], history)
    

    async def add_thread(self, user_id: str, thread: Dict[str, Any]) -> None:
        """スレッドをチャット履歴に追加"""
        chatroom = await self.get_or_create_chatroom(user_id)
        history = await load_json(chatroom["files"]["thread_history"], [])
        history.append(thread)
        await save_json(chatroom["files"]["thread_history"], history)
    
    async def clear_chat_data(self, user_id: str) -> None:
        """ユーザーのチャットデータをクリア"""
        chatroom = await self.get_or_create_chatroom(user_id)
        user_files = chatroom["files"]
        
        await save_json(user_files["chat_log"], [])
        await save_json(user_files["summary"], [])
        await save_json(user_files["user_history"], {})
        await save_json(user_files["thread_history"], [])
        await save_json(user_files["strategy_data"], {})
        
    
    async def get_chat_data(self, user_id: str) -> Tuple[List, List, Dict]:
        """ユーザーのチャットデータを取得"""
        chatroom = await self.get_or_create_chatroom(user_id)
        user_files = chatroom["files"]
        
        history = await load_json(user_files["chat_log"], [])
        summary = await load_json(user_files["summary"], [])
        user_history = await load_json(user_files["user_history"], {})
        thread_history = await load_json(user_files["thread_history"], [])
        
        return history, summary, user_history, thread_history
