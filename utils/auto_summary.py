import os
import asyncio
import logging
from utils.gpt_call import gpt_call
from utils.storage import DictStorageManager, ListStorageManager
from utils.save_and_load import save_histories, save_summaries

# ============================== #
# 全局变量与常量定义
# ============================== #
SAVEDATA_DIR = "savedata"
MAX_HISTORY = 100  # 最多保留最近 100 条消息（user+assistant 各算一条）
SUMMARY_TRIGGER = 100  # 当历史记录超过 100 条消息时，自动进行总结

# 使用StorageManager封装
history_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "histories.json"))
summary_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "summaries.json"))

user_histories = history_storage.data  # 存储用户对话历史
user_summaries = summary_storage.data  # 存储用户对话摘要

# ============================== #
# 自动摘要逻辑
# ============================== #
async def summarize_history(user_id: str):
    """为指定用户生成对话摘要"""
    history = user_histories.get(user_id, [])
    if not history:
        return

    try:
        logging.info(f"正在为用户 {user_id} 生成摘要...")
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

        summary_response = await gpt_call(
            model="gpt-4.1",
            messages=summary_prompt,
            temperature=0.3,
            max_tokens=500,
            timeout=60,
        )

        summary_text = summary_response.choices[0].message.content or ""
        
        logging.info(f"摘要成功：{summary_text}")
        
        user_summaries[user_id] = summary_text
        await asyncio.to_thread(save_summaries)
        logging.info(f"✅ 用户 {user_id} 摘要完成")

        # 清除早期对话，只保留最后 50 条
        preserved = history[-50:]
        user_histories[user_id] = preserved
        save_histories()

        logging.info(f"用户 {user_id} 的历史已清理，仅保留最近 {len(preserved)} 条对话")

    except Exception as e:
        logging.warning(f"⚠️ 为用户 {user_id} 生成摘要失败：{e}")