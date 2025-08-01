# ============================== #
# 模块导入与初始化
# ============================== #
import os
import discord
import logging
from discord.ext import commands

import discord_commands
import events
from events.trigger_events import load_triggers_off
from utils.save_and_load import load_histories, load_summaries, load_roles, load_reddit_cache, load_reddit_sent_cache

# 初始化写入日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()  # 输出到控制台
    ]
)

# 获取环境变量中的 Token
TOKEN = os.environ.get("DISCORD_TOKEN") or ""
if not TOKEN:
    raise ValueError(
        "环境变量未设置，请设置 DISCORD_TOKEN")

# 初始化 Discord bot
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)
logging.info(f"✅ 使用 discord.py 版本：{discord.__version__}")


# ============================== #
# 启动bot
# ============================== #
def main():
    try:
        discord_commands.setup_all(bot)
        events.setup_all(bot)

        load_histories()
        load_summaries()
        load_roles()
        load_triggers_off()
        load_reddit_cache()
        load_reddit_sent_cache()

        logging.info("✅ 所有模块已成功加载。")
        logging.info("🔄Bot 正在启动...")
        
        bot.run(TOKEN)
        
        logging.info("✅Bot 启动成功。")
        
    except Exception as e:
        logging.error(f"❌ 启动 bot 失败：{e}")

if __name__ == "__main__":
    main()