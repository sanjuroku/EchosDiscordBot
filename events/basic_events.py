import logging
import discord
from discord.ext import commands
from utils.constants import status_map, activity_map
from utils.storage import status_storage
# ============================== #
# bot 启动event
# ============================== #
def setup(bot: commands.Bot):
    @bot.event
    async def on_ready():
        # 加载上次保存的状态
        try:
            activity_type = None
            text = None
            activity = None
            
            data = status_storage.data
            status_str = data.get("status")
            bot_status = status_map.get(str(status_str), discord.Status.idle)
            activity_type = data.get("activity_type")
            text = data.get("text")

            if activity_type and text:
                activity_func = activity_map.get(activity_type)
                if activity_func:
                    activity = activity_func(text)
                
            logging.info(f"✅ 已恢复上次状态：{bot_status} - {activity_type} {text}") 
                
        except Exception as e:
            # 默认状态活动
            bot_status = discord.Status.idle
            text = "发出了咋办的声音"
            activity = discord.CustomActivity(name=text)
                
            logging.info(f"✅ 已设置默认状态：{bot_status} - {text}") 
                
        # 设置状态
        await bot.change_presence(status=bot_status, activity=activity)
            
        # 同步全局命令
        synced = await bot.tree.sync()
            
        logging.info(f"✅ Slash commands synced: {len(synced)} 个全局指令已注册")
            
        # 打印所有已注册的指令名称
        command_names = [cmd.name for cmd in bot.tree.get_commands()]
        logging.info(f"✅ 已注册的全局指令：{command_names}")
        
        logging.info(f"✅ 已登录为 {bot.user}")
        guild_names = [guild.name for guild in bot.guilds]
        logging.info(f"📋 当前加入了 {len(bot.guilds)} 个服务器：{', '.join(guild_names)}")