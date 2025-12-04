import asyncio
import discord
import logging
from discord.ext import commands
from discord import app_commands
from typing import Optional
from openai.types.chat import ChatCompletionMessageParam

from utils.gpt_call import gpt_call
from utils.constants import DEFAULT_SYSTEM_PROMPT, MAX_HISTORY, SUMMARY_TRIGGER, DEFAULT_MODEL
from utils.locks import get_user_lock
from utils.auto_summary import summarize_history
from utils.save_and_load import save_histories
from utils.storage import history_storage, summary_storage, role_storage, user_histories, user_summaries, user_roles

# translate_to支持的语言列表
translate_choices = [
    app_commands.Choice(name="英语 English", value="English"),
    app_commands.Choice(name="日语 Japanese", value="Japanese"),
    app_commands.Choice(name="韩语 Korean", value="Korean"),
    app_commands.Choice(name="法语 French", value="French"),
    app_commands.Choice(name="德语 German", value="German"),
    app_commands.Choice(name="西班牙语 Spanish", value="Spanish"),
    app_commands.Choice(name="中文 Chinese", value="Chinese"),
    app_commands.Choice(name="俄语 Russian", value="Russian"),
    app_commands.Choice(name="意大利语 Italian", value="Italian"),
]

# ============================== #
# /ask 指令（含translate_to功能）
# ============================== #

def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="ask", description="咋办")
    @app_commands.describe(
        prompt="想问咋办的内容",
        translate_to="（可选）翻译目标语言（从下拉选择）",
        translate_to_custom_lang="（可选）自行输入语言名称（例如：法语或者French）"
    )
    @app_commands.choices(translate_to=translate_choices)
    async def ask(
        interaction: discord.Interaction, 
        prompt: str,
        translate_to: Optional[app_commands.Choice[str]] = None,
        translate_to_custom_lang: Optional[str] = None
    ):
        await interaction.response.defer() 
        
        user_id = str(interaction.user.id)
        lock = get_user_lock(user_id)

        async with lock:
            # ============ 翻译模式 ============ #
            lang = None
            custom_lang = translate_to_custom_lang.strip() if isinstance(translate_to_custom_lang, str) and translate_to_custom_lang.strip() else None
            lang = custom_lang or (translate_to.value if translate_to else None)

            if lang:
                translate_system_prompt = "你是专业的多语种翻译助手。请将用户提供的文本翻译为指定语言，确保术语准确、语言自然，避免直译和机翻痕迹。文学性文本请遵循“信、达、雅”的标准。仅返回翻译结果，不要添加解释或多余内容。"
                translate_user_prompt = f"请将以下内容翻译成{lang}：\n\n{prompt}"

                translate_messages: list[ChatCompletionMessageParam] = [
                    {"role": "system", "content": translate_system_prompt},
                    {"role": "user", "content": translate_user_prompt}
                ]
                
                try:
                    response = await gpt_call(
                        model="gpt-4o",
                        messages=translate_messages,
                        temperature=0.5,
                        max_tokens=1000,
                        timeout=60,
                    )
                    logging.info(f"✅ 模型调用成功：{response.model}")
                    reply = response.choices[0].message.content or "❌ GPT 没有返回任何内容哦 >.<"
                    await interaction.followup.send(reply)
                    
                    logging.info(f"✅ 翻译成功：{lang} | 用户 {user_id}\n原文：\n{prompt}\n翻译后：\n{reply}")
                    return
                
                except Exception as e:
                    logging.error(f"❌ 翻译失败：{e}")
                    
                    await interaction.followup.send(f"❌ 翻译失败了，请稍后重试 >.<", ephemeral=True)
                    return
            
            # ============ 普通提问模式 ============ #
            # 获取历史记录
            history = history_storage.data.get(user_id, [])
            history.append({"role": "user", "content": prompt})

            # 裁剪用于聊天上下文
            chat_context = history[-MAX_HISTORY:]

            # 构造 messages
            messages: list[ChatCompletionMessageParam] = []

            # 1. 所有情况下都加入 user 专属或默认 role
            custom_role = user_roles.get(user_id, "")
            system_prompt = f"{DEFAULT_SYSTEM_PROMPT}\n\n[我的自定义角色设定如下，请参考我的角色设定：]\n{custom_role}" if custom_role else DEFAULT_SYSTEM_PROMPT
            messages.append({"role": "system", "content": system_prompt})

            # 2. 如果有摘要，再加一条
            if user_id in user_summaries:
                messages.append({
                    "role":
                    "user",
                    "content":
                    f"[以下是我的背景信息，供你参考]\n{user_summaries[user_id]}"
                })

            messages.extend(chat_context)

            try:
                # 调用 GPT
                response = await gpt_call(
                    model=DEFAULT_MODEL,
                    messages=messages,  # 调用包含摘要的完整消息
                    temperature=0.7,
                    max_tokens=1000,
                    timeout=60,
                )
                logging.info(f"✅ 模型调用成功：{response.model}")
                logging.info(f"用户 {user_id} 提问：{prompt}")

                reply = response.choices[0].message.content or "❌ GPT 没有返回任何内容哦 >.<"

                # 添加 AI 回复到历史
                history_storage.data[user_id].append({"role": "assistant", "content": reply})
                # 保存
                await asyncio.to_thread(save_histories)

                # 如果历史太长则先摘要
                if len(history_storage.data[user_id]) >= SUMMARY_TRIGGER:
                    logging.info(f"🔍 当前完整历史：{len(history_storage.data[user_id])}")
                    await summarize_history(user_id)

                await interaction.followup.send(reply)
                logging.info(f"✅ 回复已发送给用户 {user_id}，当前完整历史：{len(history_storage.data[user_id])}")

            except Exception as e:
                logging.error(f"❌ GPT调用出错：{e}")
                await interaction.followup.send(f"❌ GPT好像出错了  >.<", ephemeral=True)
