import logging
import pytz
from datetime import datetime
import discord
from discord.ext import commands
from utils.storage import guild_list_storage

LOG_CHANNEL_ID = 1120505368531976244

# 加入新服务器触发日志提醒
def update_guilds_json(bot: commands.Bot):
    data = [
        {
            "id": g.id,
            "name": g.name,
            "member_count": g.member_count,
            "owner_id": g.owner_id,
            "joined_at": datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S %Z")
        } for g in bot.guilds
    ]
    existing = guild_list_storage.get("guilds", []) or []
    if not isinstance(existing, list):
        existing = []
    merged = {str(g["id"]): g for g in existing}  # 用 dict 合并，防重复
    
    for g in bot.guilds:
        merged[str(g.id)] = {
            "id": g.id,
            "name": g.name,
            "member_count": g.member_count,
            "owner_id": g.owner_id,
            "joined_at": datetime.now(pytz.timezone("Asia/Tokyo")).strftime("%Y-%m-%d %H:%M:%S %Z")
        }

    guild_list_storage.set("guilds", list(merged.values()))

def setup_guild_event_handlers(bot: commands.Bot):
    @bot.event
    async def on_guild_join(guild):
        update_guilds_json(bot)
        
        log_channel = bot.get_channel(LOG_CHANNEL_ID) 
        jst = pytz.timezone("Asia/Tokyo")
        joined_time = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            logging.warning("⚠️ log_channel 不是文本频道，无法发送消息")
            return

        try:
            owner = await bot.fetch_user(guild.owner_id)
        except Exception as e:
            owner = f"未知（获取失败: {e}）"

        message = (
            f"✅ Bot 加入了新服务器：**{guild.name}**（ID: `{guild.id}`）\n"
            f"👥 拥有者：{owner}（ID: {guild.owner_id}）\n"
            f"👥 成员数：{guild.member_count}\n"
            f"🕒 加入时间：{joined_time}"
        )

        await log_channel.send(message)

        logging.info(f"✅ Bot 加入新服务器：{guild.name}（ID: {guild.id}）")
        logging.info(f"👥 拥有者：{owner}（ID: {guild.owner_id}）")
        logging.info(f"👥 成员数：{guild.member_count}")
        logging.info(f"🕒 加入时间：{joined_time}")
        for each_guild in bot.guilds:
            logging.info(f"📋 服务器名：{each_guild.name} 成员数：{each_guild.member_count}")

    @bot.event
    async def on_guild_remove(guild):
        update_guilds_json(bot) 

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        jst = pytz.timezone("Asia/Tokyo")
        removed_time = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S %Z")
        
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            logging.warning("⚠️ log_channel 不是文本频道，无法发送消息")
            return

        try:
            owner = await bot.fetch_user(guild.owner_id)
        except Exception as e:
            owner = f"未知（获取失败: {e}）"
        
        message = (
            f"❌ Bot 被移除了服务器：**{guild.name}**（ID: `{guild.id}`）\n"
            f"👥 拥有者：{owner}（ID: {guild.owner_id}）\n"
            f"👥 成员数：{guild.member_count}\n"
            f"🕒 移除时间：{removed_time}"
        )

        await log_channel.send(message)

        logging.info(f"❌ Bot 被移除了服务器：{guild.name}（ID: {guild.id}）")
        logging.info(f"👥 拥有者：{owner}（ID: {guild.owner_id}）")
        logging.info(f"👥 成员数：{guild.member_count}")
        logging.info(f"🕒 移除时间：{removed_time}")
        for each_guild in bot.guilds:
            logging.info(f"📋 服务器名：{each_guild.name} 成员数：{each_guild.member_count}")