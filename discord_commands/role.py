import discord
import logging
from discord.ext import commands
from utils.storage import user_roles
from utils.save_and_load import save_roles

# ============================== #
# /setrole 指令
# ============================== #
def setup_setrole(bot: commands.Bot) -> None:
    @bot.tree.command(name="setrole", description="设置专属的角色风格，或者希望bot记住的事情")
    async def setrole(interaction: discord.Interaction, prompt: str):
        user_id = str(interaction.user.id)
        user_roles[user_id] = prompt
        save_roles()
        await interaction.response.send_message("✅ 角色设定保存了喵！", ephemeral=True)
        
        logging.info(f"✅ 用户 {user_id} 设定了角色风格:{prompt}")


# ============================== #
# /rolecheck 指令
# ============================== #
def setup_rolecheck(bot: commands.Bot) -> None:
    @bot.tree.command(name="rolecheck", description="查看你的角色设定")
    async def rolecheck(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        prompt = user_roles.get(user_id)
        if prompt:
            await interaction.response.send_message(f"📝 你的当前角色设定是：\n\n{prompt}", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ 你还没有设置自定义角色设定。可以通过`/setrole`进行角色设置捏！", ephemeral=True)


# ============================== #
# /resetrole 指令
# ============================== #
def setup_resetrole(bot: commands.Bot) -> None:
    @bot.tree.command(name="resetrole", description="清除你的角色设定，恢复默认风格")
    async def resetrole(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id in user_roles:
            user_roles.pop(user_id)
            save_roles()
            await interaction.response.send_message("✅ 已清除你的自定义角色设定，恢复默认风格喵！", ephemeral=True)
            
            logging.info(f"✅ 用户 {user_id} 清除了自定义角色设定")
            
        else:
            await interaction.response.send_message("ℹ️ 你还没有设置过角色风格哦，当前使用的就是默认设定。可以通过`/setrole`进行角色设置捏！", ephemeral=True)

