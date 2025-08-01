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