import os
import aiohttp
import asyncpraw
import discord
import random
import asyncio
import logging
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.locks import get_reddit_lock
from utils.embed import get_random_embed_color
from utils.reddit import get_cached_posts, set_cache, is_valid_url, simplify_post, reddit_sent_cache, MAX_REDDIT_HISTORY
from utils.save_and_load import save_reddit_sent_cache

# ============================== #
# /aww 指令
# ============================== #
# 初始化 Reddit 客户端的函数
async def get_reddit():
    timeout = aiohttp.ClientTimeout(total=20)  # 设置总超时时间为 20 秒
    return asyncpraw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        user_agent=os.environ.get("REDDIT_USER_AGENT"),
        requestor_kwargs={"timeout": timeout},
    )



CUTE_SUBREDDITS = [
    "AnimalsBeingDerps", "AnimalsOnReddit", "aww", "Awww", "Birding", "birdwatching", "BirdsArentReal", "Catmemes", "Eyebleach", "Floof", "Ornithology", "parrots", "PartyParrot", "rarepuppers"
]

# 用于下拉选项
subreddit_choices = [
    app_commands.Choice(name=sub, value=sub) for sub in CUTE_SUBREDDITS
]

def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="aww", description="从Reddit上随机抽一只可爱动物")
    @app_commands.describe(subreddit="选择subreddit来源，不填则随机")
    @app_commands.choices(subreddit=subreddit_choices)
    async def aww(interaction: discord.Interaction, subreddit: Optional[app_commands.Choice[str]] = None):
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)

        # 调用初始化 Reddit 客户端的函数
        reddit = await get_reddit()
        
        posts = []
        # 根据用户选择或随机选一个 subreddit
        subreddit_name = subreddit.value if subreddit else random.choice(CUTE_SUBREDDITS)
        
        # 检查缓存
        cached = get_cached_posts(subreddit_name)
        
        if cached:
            logging.info(f"📦 使用缓存数据 r/{subreddit_name}（{len(cached)} 条）")
            posts = cached
            
        else:
            lock = get_reddit_lock(subreddit_name)
            async with lock: # 添加异步锁，避免并发请求同一 subreddit
                posts = []
                
                try:
                    # 获取前 50 条热门帖子，包含图片和视频
                    subreddit_obj = await reddit.subreddit(subreddit_name)
                    async for post in subreddit_obj.hot(limit=50):
                        if post.stickied:
                            continue

                        # 图片链接
                        if post.url.endswith((".jpg", ".jpeg", ".png", ".gif")):
                            posts.append(simplify_post(post))

                        # Reddit 原生视频（非外链）
                        elif post.is_video and isinstance(post.media, dict) and "reddit_video" in post.media:
                            posts.append(simplify_post(post))

                        # gifv（Imgur 或 Gfycat）
                        elif post.url.endswith((".mp4", ".webm", ".gifv")):
                            posts.append(simplify_post(post))

                    logging.info(f"🔍 从 r/{subreddit_name} 获取 {len(posts)} 条图片/视频帖子")
                    set_cache(subreddit_name, posts)  # 成功后设置缓存
                    
                except asyncio.TimeoutError:
                    await interaction.followup.send(f"❌ 访问 r/{subreddit_name} 超时了，请稍后再试！>.<")
                    logging.warning(f"❌ 访问 Reddit 超时：r/{subreddit_name}")
                    return
                
                except Exception as e:
                    await interaction.followup.send("❌ 发生未知错误，请稍后再试 >.<")
                    logging.exception("❌ Reddit 请求失败")
                    return
        
        if not posts:
            await interaction.followup.send("❌ 没找到合适的结果捏TT，请稍后再试 >.<")
            logging.info(f"❌ 没有找到 r/{subreddit_name} 的帖子")
            return

        # 取用户已看过的链接集合（最多保存 MAX_REDDIT_HISTORY 条）
        reddit_seen_urls = reddit_sent_cache.get(user_id, set())

        # 从 posts 中挑选没有发送过的
        unseen_posts = [post for post in posts if post["url"] not in reddit_seen_urls]

        if not unseen_posts:
            unseen_posts = posts  # 如果全都看过了就重置

        # 随机挑一个
        selected_post = random.choice(unseen_posts)
        
        # 记录这次发送过的 URL
        reddit_seen_urls.add(selected_post["url"])
        if len(reddit_seen_urls) > MAX_REDDIT_HISTORY:
            reddit_seen_urls = set(list(reddit_seen_urls)[-MAX_REDDIT_HISTORY:])  # 保留最新 N 条
        reddit_sent_cache[user_id] = reddit_seen_urls
        save_reddit_sent_cache()
        
        title = selected_post["title"]
        if len(title) > 256:
            title = title[:253] + "..."

        embed = discord.Embed(
            title=title,
            url=f"https://reddit.com{selected_post['permalink']}",
            description=f"From r/{subreddit_name}",
            color=get_random_embed_color(),
        )
        
        desc = embed.description or ''
        
        # 如果是图片或 gif
        if selected_post["url"].endswith((".jpg", ".jpeg", ".png", ".gif")):
            if is_valid_url(selected_post["url"]):
                embed.set_image(url=selected_post["url"])
            logging.info(f"🐾 图片链接：{selected_post['url']}")

        # 如果是 Reddit 原生视频
        elif (selected_post["is_video"] and selected_post["media"] and isinstance(selected_post["media"], dict) and "reddit_video" in selected_post["media"]):
            thumbnail_url = selected_post.get("thumbnail")  # 获取缩略图
            if is_valid_url(thumbnail_url):
                embed.set_image(url=thumbnail_url)
            media = selected_post.get("media") or {}
            video_url = media.get("reddit_video", {}).get("fallback_url")
            embed.description = f"{desc}\n[🐾 Click to watch / 点我看视频捏 🐾]({video_url})\n注意：Reddit 视频在这里播放没有声音哦，可以点标题查看原贴 >.<"
            logging.info(f"🐾 视频链接：{video_url}")

        # 如果是 mp4/webm
        elif selected_post["url"].endswith((".mp4", ".webm")):
            thumbnail_url = selected_post.get("thumbnail")  # 获取缩略图
            if is_valid_url(thumbnail_url):
                embed.set_image(url=thumbnail_url)
            embed.description = f"{desc}\n[🐾 Click to watch / 点我看视频捏 🐾]({selected_post['url']})\n注意：Reddit 视频在这里播放没有声音哦，可以点标题查看原贴 >.<"
            logging.info(f"🐾 mp4/webm链接：{selected_post['url']}")
        
        elif selected_post["url"].endswith(".gifv"):
            thumbnail_url = selected_post.get("thumbnail")  # 获取缩略图
            if is_valid_url(thumbnail_url):
                embed.set_image(url=thumbnail_url)
            mp4_url = selected_post["url"].replace(".gifv", ".mp4")
            embed.description = f"{desc}\n[🐾 Click to watch / 点我看视频捏 🐾]({mp4_url})\n注意：Reddit 视频在这里播放没有声音哦，可以点标题查看原贴 >.<"
            logging.info(f"🐾 gifv转mp4链接：{mp4_url}")

        logging.info(f"🐾 随机抽取了 r/{subreddit_name} 的帖子：{title} ")
        
        await reddit.close()
        await interaction.followup.send(embed=embed)