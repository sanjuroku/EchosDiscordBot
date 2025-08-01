import discord
import logging
import random
from discord.ext import commands
from utils.gpt_call import gpt_call
from utils.storage import user_roles
from utils.constants import DEFAULT_SYSTEM_PROMPT, TAROT_CARDS
from openai.types.chat import ChatCompletionMessageParam

# ============================== #
# /fortune 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="fortune", description="占卜你的今日运势并解读")
    async def fortune(interaction: discord.Interaction):
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)

        # 随机抽牌
        card_index = random.randint(0, 77)
        card_name = TAROT_CARDS[card_index]
        position = random.choice(["正位", "逆位"])

        custom_role = user_roles.get(user_id, "")
        system_prompt = f"{DEFAULT_SYSTEM_PROMPT}\n\n[我的自定义角色设定如下，请参考我的角色设定：]\n{custom_role}" if custom_role else DEFAULT_SYSTEM_PROMPT

        prompt = f"""你是一个风趣靠谱的女巫，请用轻松诙谐的语气，为我占卜今天的整体运势。可以从多种多样的方面综合评价。根据塔罗（我抽到的塔罗牌是：{card_name}（{position}）、星座、八卦、抽签（类似日本神社抽签，吉凶随机）、随机事件、今日推荐的wordle起手词（随机抽取一个5个字母的英语单词）、今日的幸运食物、今日的幸运emoji、今日的幸运颜文字、今日的小小建议等自由组合方式生成一个完整的今日运势解析。回复格式自由。请保证绝对随机，可以很差，也可以很好。"""

        messages: list[ChatCompletionMessageParam] = [{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": prompt
        }]

        try:
            response = await gpt_call(
                model="gpt-4.1",
                messages=messages,
                temperature=0.9,
                max_tokens=1000,
                timeout=60,
            )
            logging.info(f"✅ 模型调用成功：{response.model}")
            reply = response.choices[0].message.content or "❌ GPT 没有返回内容。"
            await interaction.followup.send(reply)
            
            logging.info(f"用户 {user_id} 占卜今日运势")
            logging.info(f"抽取的塔罗牌: {card_name}({position})")
            
        except Exception as e:
            await interaction.followup.send(f"❌ 出错了：{str(e)}", ephemeral=True)

