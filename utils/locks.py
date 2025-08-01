import asyncio
from typing import Dict

__all__ = ["get_user_lock", "get_reddit_lock"]

# 添加锁管理器
_user_locks: Dict[str, asyncio.Lock] = {}

# ============================== #
# 获取锁的辅助函数
# ============================== #
def get_user_lock(user_id: str) -> asyncio.Lock:
    """获取指定用户的锁对象（用于防止多次并发请求）"""
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]

# Reddit 子板块锁（防止缓存重入）
_reddit_locks: Dict[str, asyncio.Lock] = {}
def get_reddit_lock(subreddit: str) -> asyncio.Lock:
    if subreddit not in _reddit_locks:
        _reddit_locks[subreddit] = asyncio.Lock()
    return _reddit_locks[subreddit]