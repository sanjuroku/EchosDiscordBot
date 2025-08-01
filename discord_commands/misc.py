import discord
from discord.ext import commands

# ============================== #
# /buymeacoffee 指令
# ============================== #
def setup_buymeacoffee(bot: commands.Bot) -> None:
    @bot.tree.command(name="buymeacoffee", description="喜欢我可以请作者喝杯咖啡哦 :3c")
    async def buymeacoffee(interaction: discord.Interaction):
        embed = discord.Embed(
            title="☕️ Buy Me A Coffee ☕️ 请我喝杯咖啡吧 :3c",
            description="如果你喜欢 咋办 bot 或者被逗笑了一点点，\n可以点击标题通过 ko-fi 请我喝杯咖啡捏！☕️",
            url="https://ko-fi.com/kuroniko07",
            color=discord.Color.from_str("#ffcccc"),
        )
        embed.set_image(url="https://storage.ko-fi.com/cdn/kofi1.png?v=3") 
        embed.set_footer(text="🌈 咋办 bot 目前由一人开发，运行在 VPS 服务器上。\n🌈 相关指令使用的都是 GPT-4.1 模型。\n✨ 谢谢你喜欢咋办 >.< 有任何建议或反馈，也欢迎随时告诉我！\n💌 DM @kuroniko0707")

        await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================== #
# /help 指令
# ============================== #
def setup_help(bot: commands.Bot) -> None:
    @bot.tree.command(name="help", description="列出所有可用指令")
    async def help_command(interaction: discord.Interaction):
        msg = ("可用指令列表：\n"
            "💬 `/ask <问题> [可选：翻译目标语言]` - 咋办\n"
            "💭 `/choose <选项1> <选项2> ...` - 让咋办帮忙选选\n"
            "🔮 `/tarot <困惑>` - 抽一张塔罗牌解读你的困惑\n"
            "🧙‍♀️ `/fortune` - 占卜你的今日运势并解读\n"
            "🐾 `/aww <subreddit>` - 从Reddit上随机抽一只可爱动物\n"
            "🎮 `/steam <游戏名称> [可选：地区]` - 查询 Steam 游戏信息\n"
            "🌠 `/neodb <名称> [可选：媒体类型]` - 查询书影音信息\n"
            "🕒 `/timezone` - 显示当前时间与全球多个时区的对照\n\n"
            "🙋‍♀️ `/setrole <风格设定>` - 设置专属的角色风格，或者希望bot记住的事情\n"
            "🙋‍♀️ `/rolecheck` - 查看你的角色设定\n"
            "🙋‍♀️ `/resetrole` - 清除你的角色设定，恢复默认风格\n"
            "📝 `/summary` - 总结以往对话生成摘要\n"
            "📝 `/summarycheck` - 查看你的对话摘要\n"
            "😶 `/trigger <on/off>` - 开启或关闭你的发言自动触发'咋办'\n"
            "🧹 `/reset` - 重置清空所有历史\n\n"
            "🐣 `/help` - 列出所有可用指令\n"
            "🌈 `/buymeacoffee` - 如果你喜欢咋办，可以请作者喝杯咖啡哦 ☕️ :3c\n"
            "💌 有问题可以 @kuroniko0707 捏（没问题也可以）")
        await interaction.response.send_message(msg, ephemeral=True)

