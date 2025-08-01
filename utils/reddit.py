import time
import logging
from utils.save_and_load import reddit_cache_storage, reddit_sent_cache_storage, CACHE_DURATION

# 内存缓存结构：{subreddit_name: {"data": [...], "timestamp": float}}
reddit_cache = {}
# 设置用户看过的reddit帖子缓存
reddit_sent_cache = {}  # 格式：{user_id: set(url1, url2, ...)}
MAX_REDDIT_HISTORY = 20

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
# Reddit 相关缓存与函数
# ============================== #

# 获取reddit帖子
def get_cached_posts(subreddit_name: str):
    entry = reddit_cache.get(subreddit_name)
    if entry and (time.time() - entry["timestamp"]) < CACHE_DURATION:
        return entry["data"]
    return None

# 设置reddit帖子缓存
def set_cache(subreddit_name: str, posts: list):
    reddit_cache[subreddit_name] = {
        "data": posts,
        "timestamp": time.time()
    }
    save_reddit_cache()

# ============================== #
# 简化 Reddit 帖子数据函数
# ============================== #

# 检验URL是否有效
def is_valid_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("http")

def simplify_post(post):
    return {
        "title": post.title,
        "url": post.url,
        "permalink": post.permalink,
        "is_video": post.is_video,
        "media": post.media if post.is_video else None,
        "stickied": post.stickied,
        "thumbnail": post.thumbnail if is_valid_url(post.thumbnail) else None,
    }