import discord
import logging
import random
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.gpt_call import gpt_call
from utils.storage import user_roles
from utils.constants import DEFAULT_SYSTEM_PROMPT, TAROT_CARDS, DEFAULT_MODEL
from openai.types.chat import ChatCompletionMessageParam

# ============================== #
# /tarot 指令
# ============================== #
def setup(bot: commands.Bot) -> None:
    
    # spread 类型选择
    spread_choices = [
        app_commands.Choice(name="单张牌", value="1"),
        app_commands.Choice(name="三张牌", value="3"),
        app_commands.Choice(name="五张牌", value="5"),
    ]
    
    @bot.tree.command(name="tarot", description="抽一张或多张塔罗牌解读你的困惑")
    @app_commands.describe(
        wish_text="你的困惑或问题",
        spread_type="抽几张牌（为空则默认单张）"
    )
    @app_commands.choices(spread_type=spread_choices)
    
    async def tarot(
        interaction: discord.Interaction,
        wish_text: str,
        spread_type: Optional[app_commands.Choice[str]] = None
    ):
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        
        # 获取抽牌数量
        num_cards = int(spread_type.value) if spread_type else 1

        # 随机抽牌（不重复）
        drawn_indices = random.sample(range(len(TAROT_CARDS)), k=num_cards)
        drawn_cards = [TAROT_CARDS[i] for i in drawn_indices]
        drawn_positions = [random.choice(["正位", "逆位"]) for _ in range(num_cards)]
        
        # 拼接 GPT prompt
        card_text_for_prompt = "\n".join(
            f"{drawn_cards[i]}（{drawn_positions[i]}）" for i in range(num_cards)
        )

        # 获取当前角色设定
        custom_role = user_roles.get(user_id, "")
        system_prompt = f"{DEFAULT_SYSTEM_PROMPT}\n\n[我的自定义角色设定如下，请参考我的角色设定：]\n{custom_role}" if custom_role else DEFAULT_SYSTEM_PROMPT

        prompt = (
            f"你是一个有趣可信的女巫。请根据下列内容，为我提供塔罗牌解读建议：\n"
            f"我的困惑是：{wish_text}\n"
            f"我抽到的塔罗牌如下（请注意正逆位）：\n{card_text_for_prompt}\n\n"
            f"请结合这些牌的牌义进行解读。\n"
            f"- 如果是三张牌，请从过去/现在/未来的角度解读；\n"
            f"- 如果是五张牌，请根据我的疑惑自由选取合适的牌阵进行综合分析；\n"
            f"- 如果只有一张，请专注该牌的象征意义并对我的困惑给出详细回应。"
        )

        messages: list[ChatCompletionMessageParam] = [{
            "role": "system",
            "content": system_prompt
        }, {
            "role": "user",
            "content": prompt
        }]

        try:
            response = await gpt_call(
                model=DEFAULT_MODEL,
                messages=messages,
                temperature=0.8,
                max_tokens=1000,
                timeout=60,
            )
            logging.info(f"✅ 模型调用成功：{response.model}")

            choices = response.choices or []
            if not choices or not choices[0].message.content:
                reply = "❌ GPT 没有返回内容 >.<"
            else:
                reply = choices[0].message.content.strip()

            await interaction.followup.send(f"💭 你的困惑是：**{wish_text}**\n"
                                            f"🔮 你抽到的牌是：\n**{card_text_for_prompt}**\n\n"
                                            f"{reply}")
            
            logging.info(f"用户: {user_id} 占卜塔罗牌")
            logging.info(f"困惑: {wish_text}")
            logging.info(f"抽取的塔罗牌: {card_text_for_prompt}")

        except Exception as e:
            await interaction.followup.send(f"❌ 出错了：{str(e)}", ephemeral=True)

