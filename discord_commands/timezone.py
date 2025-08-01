import discord
import logging
import pytz
from discord.ext import commands
from datetime import datetime
from discord import Embed
from utils.embed import get_random_embed_color

# ============================== #
# /timezone 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="timezone", description="显示当前时间与全球多个时区的对照")
    async def timezone(interaction: discord.Interaction):
        await interaction.response.defer()

        # 定义需要展示的时区列表
        timezones = {
            "🇨🇦 加拿大（温哥华）": "America/Vancouver",
            "🇨🇦 加拿大（埃德蒙顿）": "America/Edmonton",
            "🇨🇦 加拿大（多伦多）": "America/Toronto",
            "🇺🇸 美西（洛杉矶）": "America/Los_Angeles",
            "🇺🇸 美中（芝加哥）": "America/Chicago",
            "🇺🇸 美东（纽约）": "America/New_York",
            "🇬🇧 英国（伦敦）": "Europe/London",
            "🇪🇺 西欧（巴黎）": "Europe/Paris",
            "🇨🇳 中国（北京）": "Asia/Shanghai",
            "🇲🇾 马来西亚": "Asia/Kuala_Lumpur",
            "🇸🇬 新加坡": "Asia/Singapore",
            "🇦🇺 澳大利亚（珀斯）": "Australia/Perth",
            "🇯🇵 日本": "Asia/Tokyo",
            "🇦🇺 澳大利亚（阿德莱德）": "Australia/Adelaide",
            "🇦🇺 澳大利亚（悉尼）": "Australia/Sydney"
        }

        now_utc = datetime.now(pytz.utc)
        
        # 构造纯文本内容
        lines = []
        for label, tz_name in timezones.items():
            tz = pytz.timezone(tz_name)
            local_time = now_utc.astimezone(tz)
            formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"{label} : `{formatted_time}`")

        time_text = "\n".join(lines)

        # 构建 Embed
        embed = Embed(
            title="🕒 当前时间的全球时区对照表",
            description=time_text,
            color=get_random_embed_color()
        )
        
        await interaction.followup.send(embed=embed)
        
        logging.info("✅ 已发送当前时间对照表")