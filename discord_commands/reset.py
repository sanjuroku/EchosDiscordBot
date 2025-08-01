import discord
import logging
from discord.ext import commands
from discord.ui import View, Button
from utils.storage import history_storage, summary_storage, role_storage
# ============================== #
# reset 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="reset", description="重置清空所有历史")
    async def reset(interaction: discord.Interaction):
        class ConfirmReset(View):
            def __init__(self):
                super().__init__(timeout=300)

            @discord.ui.button(label="✅ 确定一定以及肯定", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction_: discord.Interaction, button: Button):
                user_id = str(interaction_.user.id)
                history_storage.delete(user_id)
                summary_storage.delete(user_id)
                role_storage.delete(user_id)
                await interaction_.response.edit_message(content="✅ 历史记录已清空 >.<", view=None)
                logging.info(f"✅ 用户 {user_id} 清空了所有历史")

            @discord.ui.button(label="❌ 取消", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction_: discord.Interaction, button: Button):
                await interaction_.response.edit_message(content="❎ Phew, 已取消清空操作 >.<", view=None)

        await interaction.response.send_message(
            "⚠️ 你确定要清空所有历史记录吗？\n```清空对象范围：\n- /ask 的历史对话\n- /summary 以及自动摘要的历史内容\n- /setrole 存储的角色设定 ```\n⚠️ 此操作不可撤销哦 >.<", 
            view=ConfirmReset(), ephemeral=True
        )