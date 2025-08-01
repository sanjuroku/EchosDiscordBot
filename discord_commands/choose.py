import discord
import random
import logging
import re
from discord.ext import commands
from discord import app_commands

# ============================== #
# /choose 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="choose", description="让咋办帮忙选选")
    @app_commands.describe(options="请输入2个以上用空格分隔的选项")
    async def choose(interaction: discord.Interaction, options: str):
        await interaction.response.defer()

        # 分割用户输入的字符串
        choices = [c for c in re.split(r"[,\s]+", options.strip()) if c.strip()]
        if len(choices) < 2:
            await interaction.followup.send("ℹ️ 请至少提供两个选项，例如：`/choose A B C`", ephemeral=True)
            return

        # 随机选择
        result = random.choice(choices)
        
        logging.info(f"💭 选项: {options}")
        logging.info(f"💭 结果: {result}")
        
        await interaction.followup.send(f"💭 咋办寻思：**{result}**")

