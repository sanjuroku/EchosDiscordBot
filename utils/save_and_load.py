import os
from utils.storage import DictStorageManager

# ============================== #
# 全局变量与常量定义
# ============================== #
CONFIG_DIR = "config"
SAVEDATA_DIR = "savedata"

# 使用StorageManager封装
history_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "histories.json"))
summary_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "summaries.json"))
role_storage = DictStorageManager(os.path.join(CONFIG_DIR, "roles.json"))
reddit_cache_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "reddit_cache.json"))
reddit_sent_cache_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "reddit_sent_cache.json"))

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
    reddit_cache_storage.set("cache", reddit_cache)

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