import json
from typing import AsyncGenerator, Dict, Any, Optional
from colorama import Fore, Style
import anthropic
from openai import OpenAI
from datetime import datetime

# 修正したwith_retry関数をインポート
from .retry_logic import with_retry_generator

class AIStreamClient:
    """AIモデルのストリーミングレスポンスを処理するクラス"""
    
    def __init__(
        self, 
        anthropic_client: anthropic.Anthropic,
        openrouter_client: OpenAI
    ):
        self.anthropic_client = anthropic_client
        self.openrouter_client = openrouter_client
        
    async def _stream_anthropic(
        self, 
        user_input: str, 
        system_prompt: str,
        model: str = "claude-3-7-sonnet-20250219",
        max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """Anthropic APIを使用してストリーミングレスポンスを生成"""
        
        async def _stream_func():
            """with_retry_generator関数で使用する実際のストリーミング関数"""
            with self.anthropic_client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_input}
                ]
            ) as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                    yield text
        
        # リトライロジックでラップした関数を実行
        async for text in with_retry_generator(
            _stream_func,
            max_retries=5,
            retry_on_exceptions=(anthropic.APIStatusError,),
            error_messages={
                anthropic.APIStatusError: "Anthropic APIエラー",
                "429": "APIが混雑しています",
                "overloaded_error": "APIが過負荷状態です"
            }
        ):
            yield text
    
    async def _stream_openrouter(
        self, 
        user_input: str, 
        system_prompt: str,
        model: str = "anthropic/claude-3.7-sonnet",
        max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """OpenRouter APIを使用してストリーミングレスポンスを生成"""
        
        async def _stream_func():
            """実際のストリーミング処理を行う関数"""
            stream = self.openrouter_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input} 
                ],
                max_tokens=max_tokens,
                stream=True
            )
            
            print(f"\n{Fore.BLUE}Claude:{Style.RESET_ALL}", end="")
            
            async for chunk in stream:
                delta = chunk.choices[0].delta 
                if delta and delta.content:
                    print(delta.content, end="", flush=True)
                    yield delta.content
        
        # リトライロジックでラップした関数を実行
        async for text in with_retry_generator(
            _stream_func,
            max_retries=5,
            retry_on_exceptions=(Exception,),
            error_messages={
                Exception: "OpenRouter APIエラー",
                "429": "APIが混雑しています",
                "overload": "APIが過負荷状態です"
            }
        ):
            yield text
    
    async def stream_response(
        self, 
        user_input: str, 
        system_prompt: str,
        provider: str = "anthropic",
        model: Optional[str] = None,
        max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """プロバイダーに基づいてストリーミングレスポンスを生成"""
        
        if provider.lower() == "anthropic":
            model = model or "claude-3-7-sonnet-20250219"
            async for text in self._stream_anthropic(user_input, system_prompt, model, max_tokens):
                yield text
        elif provider.lower() == "openrouter":
            model = model or "anthropic/claude-3.7-sonnet"
            async for text in self._stream_openrouter(user_input, system_prompt, model, max_tokens):
                yield text
        else:
            yield json.dumps({"error": f"未知のプロバイダー: {provider}"})

# 使用例:
# ai_client = AIStreamClient(anthropic_client, openrouter_client)
# async for text in ai_client.stream_response(user_input, system_prompt, "anthropic"):
#     # テキストを処理