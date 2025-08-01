import time

from utils.save_and_load import save_reddit_cache

# 设置用户看过的reddit帖子缓存
reddit_sent_cache = {}  # 格式：{user_id: set(url1, url2, ...)}
MAX_REDDIT_HISTORY = 20

# ============================== #
# Reddit 相关缓存与函数
# ============================== #
# 内存缓存结构：{subreddit_name: {"data": [...], "timestamp": float}}
reddit_cache = {}
CACHE_DURATION = 1800 # 缓存持续时间，单位为秒（30分钟）

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