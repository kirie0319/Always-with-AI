import asyncio
from typing import Any, Callable, TypeVar, Optional, AsyncGenerator
from colorama import Fore, Style
import traceback

T = TypeVar('T')

async def with_retry_generator(
    generator_func: Callable[..., AsyncGenerator[T, None]],
    *args: Any,
    max_retries: int = 5,
    initial_backoff: float = 1.0,
    backoff_factor: float = 2.0,
    retry_on_exceptions: tuple = (Exception,),
    error_messages: dict = None,
    **kwargs: Any
) -> AsyncGenerator[T, None]:
    """
    非同期ジェネレータ関数に対する汎用的なリトライロジック
    
    Parameters:
    - generator_func: リトライする非同期ジェネレータ関数
    - args: 関数への位置引数
    - max_retries: 最大リトライ回数
    - initial_backoff: 初期バックオフ時間（秒）
    - backoff_factor: バックオフ係数
    - retry_on_exceptions: リトライする例外のタプル
    - error_messages: 例外タイプごとのエラーメッセージ辞書
    - kwargs: 関数へのキーワード引数
    
    Yields:
    - ジェネレータから生成される値
    """
    if error_messages is None:
        error_messages = {
            Exception: "エラーが発生しました",
            "429": "APIが混雑しています。時間をおいて再度お試しください。",
            "overloaded": "APIが混雑しています。時間をおいて再度お試しください。"
        }
    
    retry_count = 0
    backoff_time = initial_backoff
    
    while retry_count < max_retries:
        try:
            # 非同期ジェネレータ関数を呼び出し
            gen = generator_func(*args, **kwargs)
            async for item in gen:
                yield item
            return  # 成功したら終了
        except retry_on_exceptions as e:
            retry_count += 1
            
            # エラーメッセージの選択
            error_msg = error_messages.get(type(e), str(e))
            for key in error_messages:
                if isinstance(key, str) and key.lower() in str(e).lower():
                    error_msg = error_messages[key]
                    break
            
            if retry_count < max_retries:
                print(f"\n{Fore.YELLOW}{error_msg}。{backoff_time}秒後に再試行します...({retry_count}/{max_retries}){Style.RESET_ALL}")
                await asyncio.sleep(backoff_time)
                backoff_time *= backoff_factor
            else:
                print(f"\n{Fore.RED}最大リトライ回数に達しました。{error_msg}{Style.RESET_ALL}\n")
                print(f"詳細なエラー: {traceback.format_exc()}")
                raise  # 最大リトライ回数に達した場合は例外を再送出

async def with_retry(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 5,
    initial_backoff: float = 1.0,
    backoff_factor: float = 2.0,
    retry_on_exceptions: tuple = (Exception,),
    error_messages: dict = None,
    **kwargs: Any
) -> T:
    """
    通常の非同期関数に対する汎用的なリトライロジック
    
    Parameters:
    - func: リトライする非同期関数
    - args: 関数への位置引数
    - max_retries: 最大リトライ回数
    - initial_backoff: 初期バックオフ時間（秒）
    - backoff_factor: バックオフ係数
    - retry_on_exceptions: リトライする例外のタプル
    - error_messages: 例外タイプごとのエラーメッセージ辞書
    - kwargs: 関数へのキーワード引数
    
    Returns:
    - 関数の戻り値
    """
    if error_messages is None:
        error_messages = {
            Exception: "エラーが発生しました",
            "429": "APIが混雑しています。時間をおいて再度お試しください。",
            "overloaded": "APIが混雑しています。時間をおいて再度お試しください。"
        }
    
    retry_count = 0
    backoff_time = initial_backoff
    last_exception = None
    
    while retry_count < max_retries:
        try:
            return await func(*args, **kwargs)
        except retry_on_exceptions as e:
            retry_count += 1
            last_exception = e
            
            # エラーメッセージの選択
            error_msg = error_messages.get(type(e), str(e))
            for key in error_messages:
                if isinstance(key, str) and key.lower() in str(e).lower():
                    error_msg = error_messages[key]
                    break
            
            if retry_count < max_retries:
                print(f"\n{Fore.YELLOW}{error_msg}。{backoff_time}秒後に再試行します...({retry_count}/{max_retries}){Style.RESET_ALL}")
                await asyncio.sleep(backoff_time)
                backoff_time *= backoff_factor
            else:
                print(f"\n{Fore.RED}最大リトライ回数に達しました。{error_msg}{Style.RESET_ALL}\n")
                print(f"詳細なエラー: {traceback.format_exc()}")
    
    # 最大リトライ回数に達した場合
    raise last_exception