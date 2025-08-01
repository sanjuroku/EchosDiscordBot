from discord.ext import commands
from utils.storage import trigger_storage

# ============================== #
# 聊天记录中trigger咋办
# ============================== #
disabled_triggers: set[str] = set()

# 加载triggers设置的函数
def load_triggers_off():
    global disabled_triggers
    disabled_triggers = set(trigger_storage.data)
            
# 保存triggers_off设置的函数
def save_triggers_off():
    trigger_storage.data = list(disabled_triggers)
    trigger_storage.save()

def setup(bot: commands.Bot):
    @bot.event
    async def on_message(message):
        # 避免 bot 自己触发自己
        if message.author.bot:
            return

        user_id = str(message.author.id)
        if "咋办" in message.content and user_id not in disabled_triggers: # 跳过triggers_off用户
            await message.channel.send("咋办")

        # 为了确保其他指令还能运行
        await bot.process_commands(message)