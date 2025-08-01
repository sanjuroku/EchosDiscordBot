import time
import logging
from typing import Optional
from utils.save_and_load import save_neodb_cache, CACHE_DURATION

# 内存缓存
neodb_cache = {}

# ============================== #
# Neodb 相关缓存与函数
# ============================== #
def get_neodb_cached_result(query_key: str):
    logging.info(f"✅ get_neodb_cached_result：{query_key}")
    logging.info(f" get_neodb_cached_result 当前 neodb_cache ：{neodb_cache}")
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
