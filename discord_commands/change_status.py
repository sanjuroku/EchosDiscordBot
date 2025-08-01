import logging
from discord.ext import commands
from discord import Interaction, app_commands
from typing import Optional
from utils.constants import status_map, activity_map, OWNER_ID
from utils.storage import status_storage

status_choices = [
    app_commands.Choice(name="在线", value="在线"),
    app_commands.Choice(name="闲置", value="闲置"),
    app_commands.Choice(name="请勿打扰", value="请勿打扰"),
    app_commands.Choice(name="隐身", value="隐身"),
]

activity_choices = [
    app_commands.Choice(name="正在玩", value="正在玩"),
    app_commands.Choice(name="正在看", value="正在看"),
    app_commands.Choice(name="正在听", value="正在听"),
    app_commands.Choice(name="自定义", value="自定义"),
]

# ============================== #
# /changestatus 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="changestatus", description="更改状态和活动")
    @app_commands.choices(online_status=status_choices, activity_type=activity_choices)
    @app_commands.describe(text="活动内容（可选）")
    async def change_status(
        interaction: Interaction,
        online_status: app_commands.Choice[str],
        activity_type: Optional[app_commands.Choice[str]] = None,
        text: Optional[str] = None
    ):

        # 权限检查
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("ℹ️ 你没有权限使用这个命令哦 :3c", ephemeral=True)
            return

        try:
            status = status_map.get(online_status.value)

            activity = None
            if activity_type and text:
                activity_func = activity_map.get(activity_type.value)
                if activity_func:
                    activity = activity_func(text)

            await bot.change_presence(status=status, activity=activity)
            await interaction.response.send_message("✅ Bot 状态已更新！", ephemeral=True)
            
            # 用 StorageManager 保存设置
            status_storage.data.update({
                "status": online_status.value,
                "activity_type": activity_type.value if activity_type else "",
                "text": text or ""
            })
            status_storage.save()
            
            logging.info(f"🟢 状态已更改为 {online_status.value}" + (f" / {activity_type.value}：{text}" if activity_type and text else ""))
            
        except Exception as e:
            await interaction.response.send_message(f"❌ 出错了：{str(e)}", ephemeral=True)