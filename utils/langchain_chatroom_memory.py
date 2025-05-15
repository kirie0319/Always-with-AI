# utils/langchain_chatroom_memory.py
from langchain.schema import BaseChatMessageHistory
from langchain.memory.chat_memory import BaseChatMemory
from langchain.schema.messages import AIMessage, HumanMessage, BaseMessage
from typing import List, Dict, Any
from utils.chatroom_manager import ChatroomManager

class ChatroomMemory(BaseChatMemory):
    def __init__(self, user_id: str, chatroom_manager: ChatroomManager):
        self.user_id = str(user_id)
        self.chatroom_manager = chatroom_manager
        self.memory_key = "history"  # LangChainのデフォルト
        super().__init__()

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    async def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # JSONから履歴を読み込んでLangChain形式に変換
        _, _, _, thread_history = await self.chatroom_manager.get_chat_data(self.user_id)
        messages: List[BaseMessage] = []
        for msg in thread_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        return {self.memory_key: messages}

    async def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        # ユーザーとアシスタントの発話を履歴として保存
        if not inputs or not outputs:
            return
        user_msg = {
            "role": "user",
            "content": inputs.get("input"),
            "user_id": self.user_id,
        }
        assistant_msg = {
            "role": "assistant",
            "content": outputs.get("output"),
            "user_id": self.user_id,
        }
        await self.chatroom_manager.add_thread(self.user_id, user_msg)
        await self.chatroom_manager.add_thread(self.user_id, assistant_msg)

    async def clear(self) -> None:
        await self.chatroom_manager.clear_chat_data(self.user_id)
