import os
import time
import logging
from utils.storage import DictStorageManager

# ============================== #
# 全局变量与常量定义
# ============================== #
CONFIG_DIR = "config"
SAVEDATA_DIR = "savedata"
CACHE_DURATION = 1800 # 缓存持续时间，单位为秒（30分钟）

# 使用StorageManager封装
history_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "histories.json"))
summary_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "summaries.json"))
role_storage = DictStorageManager(os.path.join(CONFIG_DIR, "roles.json"))
reddit_cache_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "reddit_cache.json"))
reddit_sent_cache_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "reddit_sent_cache.json"))
neodb_cache_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "neodb_cache.json"))

# ============================== #
# 历史记录持久化函数
# ============================== #
def save_histories():
    """保存用户历史记录到文件"""
    history_storage.save()


def load_histories():
    """从文件加载用户历史记录"""
    global user_histories
    user_histories = history_storage.data


# ============================== #
# 摘要持久化函数
# ============================== #
def save_summaries():
    """保存用户摘要数据"""
    summary_storage.save()


def load_summaries():
    """加载用户摘要数据"""
    global user_summaries
    user_summaries = summary_storage.data
    
# ============================== #
# 角色设定持久化函数
# ============================== #
def save_roles():
    """保存用户角色设定"""
    role_storage.save()


def load_roles():
    """加载用户角色设定"""
    global user_roles
    user_roles = role_storage.data

# ============================== #
# Reddit 缓存持久化函数
# ============================== #
def save_reddit_cache():
    now = time.time()
    valid_cache = {
        key: val
        for key, val in reddit_cache.items()
        if now - val["timestamp"] < CACHE_DURATION
    }
    logging.info(f"💾 正在保存 Reddit 缓存，共 {len(valid_cache)} 条")
    reddit_cache_storage.set("cache", valid_cache)

def save_reddit_sent_cache():
    # 将 set 转为 list 存储
    serializable_cache = {uid: list(urls) for uid, urls in reddit_sent_cache.items()}
    reddit_sent_cache_storage.set("sent_cache", serializable_cache)

def load_reddit_cache():
    global reddit_cache
    reddit_cache = reddit_cache_storage.get("cache", {})

def load_reddit_sent_cache():
    global reddit_sent_cache
    raw = reddit_sent_cache_storage.get("sent_cache", {})
    reddit_sent_cache = {uid: set(urls) for uid, urls in raw.items()}

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
    
    logging.info(f" save_neodb_cache 当前 neodb_cache ：{neodb_cache}")
    logging.info(f" save_neodb_cache 当前 valid_cache ：{valid_cache}")

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
    logging.info(f" load_neodb_cache 当前 neodb_cache ：{neodb_cache}")