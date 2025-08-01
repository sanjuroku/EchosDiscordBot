import time
import logging
from typing import Optional
from utils.save_and_load import neodb_cache_storage, CACHE_DURATION

__all__ = [
    "load_neodb_cache",
    "save_neodb_cache",
    "get_neodb_cached_result",
    "set_neodb_cache",
]

# 内存缓存
neodb_cache = {}

# ============================== #
# Neodb 缓存持久化函数
# ============================== #
# 保存缓存
def save_neodb_cache():
    global neodb_cache
    now = time.time()
    
    for key, val in neodb_cache.items():
        age = now - val.get("timestamp", 0)
        logging.info(f"🔍 key: {key}, 缓存时间: {val.get('timestamp', 0)}, 年龄: {age:.2f} 秒")

    valid_cache = {
        key: val
        for key, val in neodb_cache.items()
        if now - val.get("timestamp", 0) < CACHE_DURATION
    }
    
    logging.info(f" save_neodb_cache 当前 neodb_cache ：{len(neodb_cache)}")

    logging.info(f"💾 正在保存 NeoDB 缓存，共 {len(valid_cache)} 条")
    neodb_cache_storage.set("cache", valid_cache)

# 载入缓存
def load_neodb_cache():
    global neodb_cache
    raw = neodb_cache_storage.get("cache", {})
    now = time.time()
    # 只加载有效的缓存
    neodb_cache = {
        key: val
        for key, val in raw.items()
        if now - val.get("timestamp", 0) < CACHE_DURATION
    }
    logging.info(f" load_neodb_cache 当前 neodb_cache ：{len(neodb_cache)}")

# ============================== #
# Neodb 相关缓存与函数
# ============================== #
def get_neodb_cached_result(query_key: str):
    logging.info(f"✅ get_neodb_cached_result：{query_key}")
    logging.info(f" get_neodb_cached_result 当前 neodb_cache ：{len(neodb_cache)}")
    entry = neodb_cache.get(query_key)
    if entry and (time.time() - entry["timestamp"]) < CACHE_DURATION:
        return entry["data"]
    return None

def set_neodb_cache(query_key: str, data: list):
    global neodb_cache
    neodb_cache[query_key] = {
        "data": data,
        "timestamp": time.time()
    }
    logging.info(f" set_neodb_cache 当前 neodb_cache ：{len(neodb_cache)}")
    save_neodb_cache()

