from functools import lru_cache
import asyncio
import aiofiles
import json
import os
from typing import Any, Dict, List, Optional, Union

# キャッシュサイズ設定
CACHE_SIZE = 100

# JSONデータのキャッシュ
_json_cache = {}
_json_cache_ttl = {}  # Time-to-live for cache entries
CACHE_TTL = 60  # キャッシュの有効期間（秒）

async def load_json(filepath: str, default: Any) -> Any:
    """
    JSONファイルを読み込む（キャッシュ機能付き）
    """
    current_time = asyncio.get_event_loop().time()
    
    # キャッシュが有効かチェック
    if filepath in _json_cache and filepath in _json_cache_ttl:
        if current_time - _json_cache_ttl[filepath] < CACHE_TTL:
            return _json_cache[filepath]
    
    try:
        # ファイルが存在するかチェック
        if not os.path.exists(filepath):
            _json_cache[filepath] = default
            _json_cache_ttl[filepath] = current_time
            return default
        
        async with aiofiles.open(filepath, "r", encoding='utf-8') as f:
            content = await f.read()
            try:
                data = json.loads(content)
                # キャッシュを更新
                _json_cache[filepath] = data
                _json_cache_ttl[filepath] = current_time
                return data
            except json.JSONDecodeError:
                _json_cache[filepath] = default
                _json_cache_ttl[filepath] = current_time
                return default
    except FileNotFoundError:
        _json_cache[filepath] = default
        _json_cache_ttl[filepath] = current_time
        return default

async def save_json(filepath: str, data: Any) -> None:
    """
    JSONファイルを保存し、キャッシュも更新する
    """
    # ディレクトリが存在することを確認
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    async with aiofiles.open(filepath, "w", encoding='utf-8') as f:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        await f.write(json_str)
    
    # キャッシュを更新
    _json_cache[filepath] = data
    _json_cache_ttl[filepath] = asyncio.get_event_loop().time()

async def to_pretty_json(data: Any) -> str:
    """
    データを整形されたJSON文字列に変換
    """
    return json.dumps(data, ensure_ascii=False, indent=2)

# キャッシュをクリアする関数
def clear_cache(filepath: Optional[str] = None) -> None:
    """
    特定のファイルまたはすべてのキャッシュをクリア
    """
    if filepath:
        if filepath in _json_cache:
            del _json_cache[filepath]
        if filepath in _json_cache_ttl:
            del _json_cache_ttl[filepath]
    else:
        _json_cache.clear()
        _json_cache_ttl.clear()