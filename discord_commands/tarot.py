import discord
import logging
import random
from discord.ext import commands
from utils.gpt_call import gpt_call
from utils.storage import user_roles
from utils.constants import DEFAULT_SYSTEM_PROMPT, TAROT_CARDS
from openai.types.chat import ChatCompletionMessageParam

# ============================== #
# /tarot 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="tarot", description="抽一张塔罗牌解读你的困惑")
    async def tarot(interaction: discord.Interaction, wish_text: str):
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)

        # 随机抽牌
        card_index = random.randint(0, 77)
        card_name = TAROT_CARDS[card_index]
        position = random.choice(["正位", "逆位"])

        # 获取当前角色设定
        custom_role = user_roles.get(user_id, "")
        system_prompt = f"{DEFAULT_SYSTEM_PROMPT}\n\n[我的自定义角色设定如下，请参考我的角色设定：]\n{custom_role}" if custom_role else DEFAULT_SYSTEM_PROMPT

        prompt = f"""请扮演一个有趣可信的女巫。我的困惑是：{wish_text}。
        我抽到的塔罗牌是：{card_name}（{position}），请结合这张牌的含义（注意是{position}），详细地解读这张牌，对我的困惑进行详细的解读和建议。"""

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
                temperature=0.8,
                max_tokens=1000,
                timeout=60,
            )
            logging.info(f"✅ 模型调用成功：{response.model}")
            reply = response.choices[0].message.content or "❌ GPT 没有返回内容。"
            await interaction.followup.send(f"你的困惑是：**{wish_text}**\n"
                                            f"你抽到的牌是：**{card_name}（{position}）**\n\n"
                                            f"{reply}")
            
            logging.info(f"用户: {user_id} 占卜塔罗牌")
            logging.info(f"困惑: {wish_text}")
            logging.info(f"抽取的塔罗牌: {card_name}({position})")

        except Exception as e:
            await interaction.followup.send(f"❌ 出错了：{str(e)}", ephemeral=True)

