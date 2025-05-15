import os
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from colorama import Fore, Style
from openai import AsyncOpenAI
from datetime import datetime

# 修正したwith_retry関数をインポート
from .retry_logic import with_retry_generator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AIOpenRouterStreamClient:
    """AIモデルのストリーミングレスポンスを処理するクラス"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.openrouter_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

        if not self.openrouter_client.api_key:
            raise ValueError("OpenRouter API key is required")

        self.openrouter_supported_models = [
            "openai/gpt-4.1",
            "anthropic/claude-3.7-sonnet"
        ]
    
    async def _stream_openrouter(
        self, 
        user_input: str, 
        system_prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """OpenRouter APIを使用してストリーミングレスポンスを生成
        
        モデルの優先順位:
        1. 指定されたモデル
        2. Claude (anthropic/claude-3.7-sonnet)
        3. OpenAI (openai/gpt-4.1)
        """
        # デフォルトモデルの設定
        models_to_try = [
            model,
            "anthropic/claude-3.7-sonnet", 
            "openai/gpt-4.1"
        ]
        models_to_try = [m for m in models_to_try if m is not None]
        
        last_exception = None
        for current_model in models_to_try:
            try:
                async def _stream_func():
                    """実際のストリーミング処理を行う関数"""
                    stream = await self.openrouter_client.chat.completions.create(
                        model=current_model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_input} 
                        ],
                        max_tokens=max_tokens,
                        stream=True,
                        temperature=0
                    )
                    
                    print(f"\n{Fore.BLUE}Model {current_model}:{Style.RESET_ALL}", end="")
                    
                    async for chunk in stream:
                        delta = chunk.choices[0].delta 
                        if delta and delta.content:
                            print(delta.content, end="", flush=True)
                            yield delta.content
                
                # リトライロジックでラップした関数を実行
                async for text in with_retry_generator(
                    _stream_func,
                    max_retries=2,
                    retry_on_exceptions=(Exception,),
                    error_messages={
                        Exception: f"OpenRouter APIエラー ({current_model})",
                        "429": "APIが混雑しています",
                        "overload": "APIが過負荷状態です"
                    }
                ):
                    yield text
                
                # If we successfully yield text, break the loop
                return
            
            except Exception as e:
                logging.warning(f"Failed to stream with model {current_model}: {str(e)}")
                last_exception = e
                continue
        
        # If all models fail
        logging.error("All models failed to generate a response")
        raise last_exception or ValueError("No models could generate a response")
    
    async def stream_response(
        self, 
        user_input: str, 
        system_prompt: str,
        provider: str = "openrouter",
        model: Optional[str] = None,
        max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """プロバイダーに基づいてストリーミングレスポンスを生成"""
        if provider.lower() == "openrouter":
            if not model:
                model = "anthropic/claude-3.7-sonnet"
            
            if model not in self.openrouter_supported_models:
                logging.warning(f"Model {model} not in supported list. Using default.")
                model = "anthropic/claude-3.7-sonnet"
            
            async for text in self._stream_openrouter(user_input, system_prompt, model, max_tokens):
                yield text
        else:
            logging.error(f"Unsupported provider: {provider}")
            raise ValueError(f"Provider {provider} is not supported")

# 使用例:
# ai_client = AIStreamClient(anthropic_client, openrouter_client)
# async for text in ai_client.stream_response(user_input, system_prompt, "anthropic"):
#     # テキストを処理