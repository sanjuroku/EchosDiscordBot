"""
封装 GPT API 的调用，并对常见异常进行统一处理。
"""

import os
import asyncio
import socket
import logging
from openai import OpenAI, OpenAIError, RateLimitError

__all__ = ["gpt_call"]

# 获取环境变量中的 Token
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") or ""
if not OPENAI_API_KEY:
    raise ValueError(
        "环境变量未设置，请设置 OPENAI_API_KEY")

# 初始化 OpenAI 客户端
client = OpenAI(api_key=OPENAI_API_KEY)

# ============================== #
# gpt_call 函数
# ============================== #
async def gpt_call(*args, **kwargs):

    def sync_call():
        try:
            return client.chat.completions.create(*args, **kwargs)
        except RateLimitError as e:
            logging.warning("GPT 被限流了。")
            raise RuntimeError("😵 GPT 太忙了，限流了，请稍后再试 >.<") from e
        except socket.timeout as e:
            logging.warning("GPT 请求超时。")
            raise RuntimeError("⌛ 请求超时啦，请稍后重试～") from e
        except OpenAIError as e:
            logging.warning("OpenAI 返回错误。")
            raise RuntimeError(f"❌ OpenAI 返回错误：{str(e)}") from e
        except Exception as e:
            logging.warning("未知错误。")
            raise RuntimeError(f"❌ 未知错误：{str(e)}") from e

    return await asyncio.to_thread(sync_call)