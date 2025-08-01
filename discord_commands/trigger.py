import discord
import logging
from discord.ext import commands
from discord import app_commands
from utils.storage import trigger_storage
from events.trigger_events import load_triggers_off, save_triggers_off, disabled_triggers

# ============================== #
# /trigger 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="trigger", description="开启或关闭你的发言自动触发'咋办'")
    @app_commands.describe(mode="开启或关闭你的发言自动触发咋办（on/off）")
    @app_commands.choices(mode=[
        app_commands.Choice(name="开启 / on", value="on"),
        app_commands.Choice(name="关闭 / off", value="off")
    ])
    async def trigger_control(interaction: discord.Interaction, mode: app_commands.Choice[str]):
        user_id = str(interaction.user.id)
        
        if mode.value == "off":
            disabled_triggers.add(user_id)
            save_triggers_off()
            await interaction.response.send_message("😶 已关闭自动触发`咋办` >.<", ephemeral=True)
        else:
            if user_id in disabled_triggers:
                disabled_triggers.remove(user_id)
                save_triggers_off()
            await interaction.response.send_message("😮 已开启自动触发`咋办` >.<", ephemeral=True)
        
        logging.info(f"🛠 用户 {user_id} 设置触发状态为 {mode.value}")