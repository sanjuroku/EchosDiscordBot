import discord
import logging
import asyncio
from discord.ext import commands
from utils.gpt_call import gpt_call
from utils.storage import user_histories, user_summaries
from utils.save_and_load import save_summaries
from utils.constants import DEFAULT_MODEL

# ============================== #
# /summary 指令
# ============================== #
def setup_summary(bot: commands.Bot) -> None:
    @bot.tree.command(name="summary", description="总结以往对话生成摘要")
    async def summary(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        """为指定用户手动生成对话摘要"""
        user_id = str(interaction.user.id)
        history = user_histories.get(user_id, [])
        if not history:
            await interaction.response.send_message("ℹ️ 还没有任何历史记录哦，无法生成摘要>.<", ephemeral=True)
            return

        try:
            logging.info(f"正在为用户 {user_id} 手动生成摘要...")
            logging.info(f"摘要开始前的历史内容：{len(history)}")
            
            history_text = "\n".join([
                f"User：{msg['content']}\n" if msg["role"] == "user" else f"Assistant：{msg['content']}\n"
                for msg in history if msg["role"] in ["user", "assistant"]
            ])

            summary_prompt = [
                {
                "role":
                "system",
                "content":
                "请你在1000字以内总结用户和GPT之间从头到尾的所有历史对话，用于后续对话的 context 使用。请使用第三人称、概括性语言，不要重复原话，不要加入评论或判断。重点总结用户的行为特征、情绪倾向、风格偏好和主要话题。\n"
                },
                {
                "role": "user",
                "content": f"以下是完整的对话历史：\n\n{history_text}"
                }
            ]
            
            #logging.info(f"摘要内容：{summary_prompt}")

            summary_response = await gpt_call(
                model=DEFAULT_MODEL,
                messages=summary_prompt,
                temperature=0.3,
                max_tokens=1000,
                timeout=60,
            )

            choices = summary_response.choices or []
            if not choices or not choices[0].message.content:
                raise ValueError("GPT 没有返回摘要内容")
            summary_text = choices[0].message.content.strip()
            
            logging.info(f"摘要成功：{summary_text}")
            
            user_summaries[user_id] = summary_text
            await asyncio.to_thread(save_summaries)
            
            await interaction.followup.send("✅ 手动生成摘要成功！可以通过`/summarycheck`进行确认>.<", ephemeral=True)

            logging.info(f"✅ 用户 {user_id} 手动摘要完成")

        except Exception as e:
            await interaction.followup.send("⚠️ 生成摘要失败TT，请稍后重试。", ephemeral=True)
            logging.warning(f"⚠️ 为用户 {user_id} 手动生成摘要失败：{e}")

# ============================== #
# summarycheck 指令
# ============================== #
def setup_summarycheck(bot: commands.Bot) -> None:
    @bot.tree.command(name="summarycheck", description="查看你的对话摘要")
    async def summarycheck(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        summary_text = user_summaries.get(user_id)

        if summary_text:
            await interaction.response.send_message(
                f"📄 这是你的对话摘要：\n\n```{summary_text}```", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ 当前还没有摘要哦！", ephemeral=True)