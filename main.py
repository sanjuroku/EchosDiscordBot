# ============================== #
# 模块导入与初始化
# ============================== #
import os
import json
import discord
import random
import asyncio
import pytz
import logging
import asyncpraw
from discord.ext import commands
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from datetime import datetime
from asyncio_throttle.throttler import Throttler
from discord import Interaction, Embed, app_commands
from typing import Optional
import aiohttp
import re

#写入日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()  # 输出到控制台
    ]
)

# 获取环境变量中的 Token
TOKEN = os.environ.get("DISCORD_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if TOKEN is None or OPENAI_API_KEY is None:
    raise ValueError(
        "环境变量未设置，请设置 DISCORD_TOKEN 和 OPENAI_API_KEY")

# 添加锁管理器
user_locks: dict[str, asyncio.Lock] = {}

# 每5秒最多5次
throttler = Throttler(rate_limit=5, period=5)


async def send_message(channel, content):
    async with throttler:
        await channel.send(content)


# gpt_call
async def gpt_call(*args, **kwargs):

    def sync_call():
        return client.chat.completions.create(*args, **kwargs)

    return await asyncio.to_thread(sync_call)


# 初始化 Discord bot
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# 初始化 OpenAI 客户端
client = OpenAI(api_key=OPENAI_API_KEY)

# ============================== #
# 全局变量与常量定义
# ============================== #
user_histories = {}  # 存储用户对话历史
user_summaries = {}  # 存储用户对话摘要
user_roles = {}  # 存储用户角色设定

MAX_HISTORY = 100  # 最多保留最近 100 条消息（user+assistant 各算一条）
SUMMARY_TRIGGER = 100  # 当历史记录超过 100 条消息时，自动进行总结
HISTORY_FILE = "histories.json"
SUMMARY_FILE = "summaries.json"
ROLE_FILE = "roles.json"

# 默认 System Prompt
DEFAULT_SYSTEM_PROMPT = "你是一个温柔、聪明、擅长倾听的 AI 小助手，名字是咋办。\n请你认真回答用户的问题。默认用户都为女性，使用女性代称，性别优先词为她、她们，不使用女性歧视的词语，禁止称呼用户小仙女、小姐姐。\n禁止油腻、卖弄、邀功。如果你不知道答案，请诚实地回答不知道，不要编造内容。\n你的语言风格亲切可爱，可以在聊天中加点轻松的颜文字、emoji表情。\n回复内容不要太啰嗦，保证在800字以内。\n当用户没有说其他内容，只有“咋办”这两个字的时候，你就只能回复“咋办”两个字，不准加任何的符号或者句子，其他时候正常对话。"


# ============================== #
# 获取锁的辅助函数
# ============================== #
def get_user_lock(user_id: str) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]


# ============================== #
# 历史记录持久化函数
# ============================== #
def save_histories():
    """保存所有用户的历史记录到文件"""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(user_histories, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"保存历史记录出错：{e}")


def load_histories():
    """从文件加载用户历史记录"""
    global user_histories
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                user_histories = json.load(f)
            logging.info(f"✅ 已从 {HISTORY_FILE} 加载历史记录，共 {len(user_histories)} 个用户")
        except Exception as e:
            logging.warning(f"⚠️ 读取历史记录失败，已忽略：{e}")
            user_histories = {}
    else:
        user_histories = {}


# ============================== #
# 摘要持久化函数
# ============================== #
def save_summaries():
    """保存用户摘要数据"""
    try:
        with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
            json.dump(user_summaries, f, ensure_ascii=False, indent=2)
            
            logging.info(f"✅ 已保存摘要到 {SUMMARY_FILE}，共 {len(user_summaries)} 个用户")
            
    except Exception as e:
        logging.error(f"❌ 保存摘要失败：{e}")


def load_summaries():
    """加载用户摘要数据"""
    global user_summaries
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
                user_summaries = json.load(f)
            logging.info(f"✅ 已从 {SUMMARY_FILE} 加载摘要，共 {len(user_summaries)} 个用户")
        except Exception as e:
            logging.warning(f"摘要读取失败，已忽略：{e}")
            user_summaries = {}
    else:
        user_summaries = {}


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
            "请你总结用户和GPT之间从头到尾的所有历史对话，用于后续对话的 context 使用。请使用第三人称、概括性语言，不要重复原话，不要加入评论或判断。重点总结用户的行为特征、情绪倾向、风格偏好和主要话题。\n"
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


# ============================== #
# 角色设定持久化函数
# ============================== #
def save_roles():
    """保存用户角色设定"""
    try:
        with open(ROLE_FILE, "w", encoding="utf-8") as f:
            json.dump(user_roles, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"❌ 保存 role 失败：{e}")


def load_roles():
    """加载用户角色设定"""
    global user_roles
    if os.path.exists(ROLE_FILE):
        try:
            with open(ROLE_FILE, "r", encoding="utf-8") as f:
                user_roles = json.load(f)
            logging.info(f"✅ 已从 {ROLE_FILE} 加载用户 role，共 {len(user_roles)} 个")
        except Exception as e:
            logging.warning(f"⚠️ 读取 role 失败，已忽略：{e}")
            user_roles = {}
    else:
        user_roles = {}


# ============================== #
# bot 启动
# ============================== #
status_map = {
    "在线": discord.Status.online,
    "闲置": discord.Status.idle,
    "请勿打扰": discord.Status.dnd,
    "隐身": discord.Status.invisible
}

activity_map = {
    "正在玩": lambda text: discord.Game(name=text),
    "正在看": lambda text: discord.Activity(type=discord.ActivityType.watching, name=text),
    "正在听": lambda text: discord.Activity(type=discord.ActivityType.listening, name=text),
    "自定义": lambda text: discord.CustomActivity(name=text)
}

@bot.event
async def on_ready():
    try:
        activity_type = None
        text = None
        activity = None
        
        # 加载上次保存的状态
        if os.path.exists("status_config.json"):
            with open("status_config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
            
            status = status_map.get(data.get("status"), discord.Status.idle)
            activity_type = data.get("activity_type")
            text = data.get("text")

            if activity_type and text:
                activity_func = activity_map.get(activity_type)
                if activity_func:
                    activity = activity_func(text)
            
            logging.info(f"✅ 已恢复上次状态：{status} - {activity_type} {text}") 
            
        else:
            # 默认状态活动
            status = discord.Status.idle
            text = "发出了咋办的声音"
            activity = discord.CustomActivity(name=text)
            
            logging.info(f"✅ 已设置默认状态：{status} - {text}") 
            
        # 设置状态
        await bot.change_presence(status=status, activity=activity)
        
        # 同步全局命令
        synced = await bot.tree.sync()
        
        logging.info(f"✅ Slash commands synced: {len(synced)} 个全局指令已注册")
        
        # 打印所有已注册的指令名称
        command_names = [cmd.name for cmd in bot.tree.get_commands()]
        logging.info(f"✅ 已注册的全局指令：{command_names}")

    except Exception as e:
        logging.error(e)
    logging.info(f"✅ 已登录为 {bot.user}")


# ============================== #
# 聊天记录中trigger咋办
# ============================== #
TRIGGER_FILE = "disabled_triggers.json"
disabled_triggers: set[str] = set()

# 加载triggers设置的函数
def load_triggers_off():
    global disabled_triggers
    if os.path.exists(TRIGGER_FILE):
        try:
            with open(TRIGGER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                disabled_triggers = set(data)
                logging.info(f"✅ 已加载triggers_off设置，共 {len(disabled_triggers)} 个用户")
        except Exception as e:
            logging.warning(f"⚠️ 加载triggers_off设置失败：{e}")
            disabled_triggers = set()
            
# 保存triggers_off设置的函数
def save_triggers_off():
    try:
        with open(TRIGGER_FILE, "w", encoding="utf-8") as f:
            json.dump(list(disabled_triggers), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"❌ 保存triggers_off设置失败：{e}")
        
@bot.event
async def on_message(message):
    # 避免 bot 自己触发自己
    if message.author.bot:
        return

    user_id = str(message.author.id)
    if "咋办" in message.content and user_id not in disabled_triggers: # 跳过triggers_off用户
        await message.channel.send("咋办")

    # 为了确保其他指令还能运行
    await bot.process_commands(message)


# ============================== #
# ask 指令
# ============================== #
@bot.tree.command(name="ask", description="咋办")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer() 
    user_id = str(interaction.user.id)
    lock = get_user_lock(user_id)

    async with lock:
        # 获取历史记录
        history = user_histories.get(user_id, [])
        history.append({"role": "user", "content": prompt})

        # 裁剪用于聊天上下文
        chat_context = history[-MAX_HISTORY:]

        # 构造 messages
        messages: list[ChatCompletionMessageParam] = []

        # 1. 所有情况下都加入 user 专属或默认 role
        custom_role = user_roles.get(user_id, "")
        system_prompt = f"{DEFAULT_SYSTEM_PROMPT}\n\n[用户自定义角色设定如下，请参考用户的角色设定：]\n{custom_role}" if custom_role else DEFAULT_SYSTEM_PROMPT
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
            # response = client.chat.completions.create(
            response = await gpt_call(
                model="gpt-4.1",
                messages=messages,  # 调用包含摘要的完整消息
                temperature=0.7,
                max_tokens=1000,
                timeout=60,
            )
            logging.info(f"✅ 模型调用成功：{response.model}")
            logging.info(f"用户 {user_id} 提问：{prompt}")

            reply = response.choices[0].message.content or "GPT 没有返回内容。"

            # 添加 AI 回复到历史
            history.append({"role": "assistant", "content": reply})

            # 限制历史长度 & 保存
            user_histories[user_id] = history
            save_histories()

            # 如果历史太长则先摘要
            if len(history) >= SUMMARY_TRIGGER:
                logging.info(f"🔍 当前完整历史：{len(user_histories[user_id])}")
                await summarize_history(user_id)

            await interaction.followup.send(reply)
            logging.info(f"✅ 回复已发送给用户 {user_id}，当前历史记录条数: {len(history)}")

        except Exception as e:
            logging.error(f"❌ GPT调用出错：{e}")
            await interaction.followup.send(f"❌ 出错了：{str(e)}", ephemeral=True)


# ============================== #
# choose 指令
# ============================== #
@bot.tree.command(name="choose", description="让咋办帮忙选选")
async def choose(interaction: discord.Interaction, options: str):
    await interaction.response.defer()

    # 分割用户输入的字符串
    choices = options.strip().split()
    if len(choices) < 2:
        await interaction.followup.send("ℹ️ 请至少提供两个选项，例如：`/choose A B C`", ephemeral=True)
        return

    # 随机选择
    result = random.choice(choices)
    
    logging.info(f"💭 选项: {options}")
    logging.info(f"💭 结果: {result}")
    
    await interaction.followup.send(f"💭 咋办寻思：**{result}**")


# ============================== #
# setrole 指令
# ============================== #
@bot.tree.command(name="setrole", description="设置专属的角色风格，或者希望bot记住的事情")
async def setrole(interaction: discord.Interaction, prompt: str):
    user_id = str(interaction.user.id)
    user_roles[user_id] = prompt
    save_roles()
    await interaction.response.send_message("✅ 角色设定保存了喵！", ephemeral=True)
    
    logging.info(f"✅ 用户 {user_id} 设定了角色风格:{prompt}")


# ============================== #
# rolecheck 指令
# ============================== #
@bot.tree.command(name="rolecheck", description="查看你的角色设定")
async def rolecheck(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    prompt = user_roles.get(user_id)
    if prompt:
        await interaction.response.send_message(f"📝 你的当前角色设定是：\n\n{prompt}", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ 你还没有设置自定义角色设定。可以通过`/setrole`进行角色设置捏！", ephemeral=True)


# ============================== #
# resetrole 指令
# ============================== #
@bot.tree.command(name="resetrole", description="清除你的角色设定，恢复默认风格")
async def resetrole(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in user_roles:
        user_roles.pop(user_id)
        save_roles()
        await interaction.response.send_message("✅ 已清除你的自定义角色设定，恢复默认风格喵！", ephemeral=True)
        
        logging.info(f"✅ 用户 {user_id} 清除了自定义角色设定")
        
    else:
        await interaction.response.send_message("ℹ️ 你还没有设置过角色风格哦，当前使用的就是默认设定。可以通过`/setrole`进行角色设置捏！", ephemeral=True)


# ============================== #
# tarot 指令
# ============================== #

# 塔罗牌列表
TAROT_CARDS = [
    "愚人", "魔术师", "女祭司", "女皇", "皇帝", "教皇", "恋人", "战车", "力量", "隐者", "命运之轮", "正义",
    "倒吊人", "死神", "节制", "恶魔", "塔", "星星", "月亮", "太阳", "审判", "世界", "权杖一", "权杖二",
    "权杖三", "权杖四", "权杖五", "权杖六", "权杖七", "权杖八", "权杖九", "权杖十", "权杖侍者", "权杖骑士",
    "权杖皇后", "权杖国王", "圣杯一", "圣杯二", "圣杯三", "圣杯四", "圣杯五", "圣杯六", "圣杯七", "圣杯八",
    "圣杯九", "圣杯十", "圣杯侍者", "圣杯骑士", "圣杯皇后", "圣杯国王", "宝剑一", "宝剑二", "宝剑三", "宝剑四",
    "宝剑五", "宝剑六", "宝剑七", "宝剑八", "宝剑九", "宝剑十", "宝剑侍者", "宝剑骑士", "宝剑皇后", "宝剑国王",
    "星币一", "星币二", "星币三", "星币四", "星币五", "星币六", "星币七", "星币八", "星币九", "星币十",
    "星币侍者", "星币骑士", "星币皇后", "星币国王"
]


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
    system_prompt = f"{DEFAULT_SYSTEM_PROMPT}\n\n[用户自定义角色设定如下，请参考用户的角色设定：]\n{custom_role}" if custom_role else DEFAULT_SYSTEM_PROMPT

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


# ============================== #
# fortune 指令
# ============================== #
@bot.tree.command(name="fortune", description="占卜你的今日运势并解读")
async def fortune(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)

    # 随机抽牌
    card_index = random.randint(0, 77)
    card_name = TAROT_CARDS[card_index]
    position = random.choice(["正位", "逆位"])

    custom_role = user_roles.get(user_id, "")
    system_prompt = f"{DEFAULT_SYSTEM_PROMPT}\n\n[用户自定义角色设定如下，请参考用户的角色设定：]\n{custom_role}" if custom_role else DEFAULT_SYSTEM_PROMPT

    prompt = f"""你是一个风趣靠谱的女巫，请用轻松诙谐的语气，为我占卜今天的整体运势。可以从多种多样的方面综合评价。根据塔罗（用户抽到的塔罗牌是：{card_name}（{position}）、星座、八卦、抽签（类似日本神社抽签，吉凶随机）、随机事件、今日推荐的wordle起手词（随机抽取一个5个字母的英语单词）、今日的幸运食物、今日的幸运emoji、今日的幸运颜文字、今日的小小建议等自由组合方式生成一个完整的今日运势解析。回复格式自由。请保证绝对随机，可以很差，也可以很好。"""

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


# ============================== #
# timezone 指令
# ============================== #
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
    time_table = []

    for label, tz_name in timezones.items():
        tz = pytz.timezone(tz_name)
        local_time = now_utc.astimezone(tz)
        formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S")
        time_table.append(f"{label}：`{formatted_time}`")

    message = "🕒 当前时间对照表：\n\n" + "\n".join(time_table)
    await interaction.followup.send(message)
    
    logging.info("✅ 已发送当前时间对照表")


# ============================== #
# /steam 指令：查询游戏信息
# ============================== #

# 可选地区列表
region_choices = [
    app_commands.Choice(name="国区（人民币）", value="cn"),
    app_commands.Choice(name="美区（美元）", value="us"),
    app_commands.Choice(name="日区（日元）", value="jp"),
    app_commands.Choice(name="港区（港币）", value="hk"),
    app_commands.Choice(name="马来西亚区（林吉特）", value="my"),
    app_commands.Choice(name="加拿大区（加元）", value="ca"),
    app_commands.Choice(name="欧洲区（欧元）", value="eu"),
    app_commands.Choice(name="俄区（卢布）", value="ru"),
    app_commands.Choice(name="土区（土耳其里拉）", value="tr"),
    app_commands.Choice(name="阿区（阿根廷比索）", value="ar"),
]


# 1. 让 GPT 返回标准中文和英文游戏名
async def get_standard_names_by_gpt(game_name: str) -> Optional[tuple]:
    prompt = ("请你根据下列用户输入的 Steam 游戏名，返回该游戏的标准官方中文名称和英文名称。\n"
              "格式为：\n中文名：xxx\n英文名：yyy\n"
              "用户输入：" + game_name)
    # 调用现有的 gpt_call
    response = await gpt_call(model="gpt-4.1",
                              messages=[{
                                  "role": "user",
                                  "content": prompt
                              }],
                              temperature=0.1,
                              max_tokens=50,
                              timeout=20)
    logging.info(f"✅ 模型调用成功：{response.model}")
    logging.info(f"GPT返回：\n{response.choices[0].message.content}")
    content = (response.choices[0].message.content or "").strip()
    # 正则匹配
    zh_match = re.search(r"中文名[:：]\s*(.+)", content)
    en_match = re.search(r"英文名[:：]\s*(.+)", content)
    zh_name = zh_match.group(1).strip() if zh_match else None
    en_name = en_match.group(1).strip() if en_match else None
    """ logging.info(
        f"正则匹配结果：\n"
        f"  中文匹配：{zh_match}\n"
        f"  英文匹配：{en_match}\n"
        f"  中文名称：{zh_name}\n"
        f"  英文名称：{en_name}"
    ) """
    return (zh_name, en_name) if zh_name or en_name else None


# 2. 封装 steam storesearch 搜索
async def steam_fuzzy_search(session, search_name, region_code, lang):
    search_url = (
        f"https://store.steampowered.com/api/storesearch/?term={search_name}&cc={region_code}&l={lang}"
    )
    async with session.get(search_url) as resp:
        data = await resp.json()

    items = data.get("items", [])
    if not items:
        return None

    lower_input = search_name.lower()

    # 1. 查找完全匹配（中文或英文）
    for item in items:
        if item["name"].lower() == lower_input:
            return item

    # 2. 查找包含匹配，避免提及数字
    for item in items:
        name = item["name"].lower()
        if lower_input in name and not re.search(r'\d', name.replace(lower_input, '')):
            return item

    # 3. 回退模糊的第一个
    return items[0]


@bot.tree.command(name="steam", description="查询 Steam 游戏信息")
@app_commands.describe(game_name="游戏名称", region="查询地区（默认国区）")
@app_commands.choices(region=region_choices)
async def steam(interaction: Interaction,
                game_name: str,
                region: Optional[app_commands.Choice[str]] = None):
    await interaction.response.defer()

    region_code = region.value if region else "cn"
    region_display = region.name if region else "国区（人民币）"

    # 1. GPT 标准化游戏名
    names = await get_standard_names_by_gpt(game_name)
    if not names:
        await interaction.followup.send("❌ 未能标准化游戏名，请检查输入。", ephemeral=True)
        return
    zh_name, en_name = names

    # 2. 依次用"中文名-英文名-原始名"去 Steam 搜索（优先中文）
    async with aiohttp.ClientSession() as session:
        found = None
        app_id = None
        for try_name in [zh_name, en_name, game_name]:
            if not try_name:
                continue
            found = await steam_fuzzy_search(session, try_name, region_code,
                                             "zh")
            if found:
                app_id = found["id"]
                break

        if not app_id:
            await interaction.followup.send("❌ Steam商店未找到匹配的游戏，请检查输入。", ephemeral=True)
            return

        # 3. 获取游戏详情，默认cn和us
        zh_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cn&l=zh"
        en_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&l=en"
        logging.info(f"🔍 正在搜索游戏：{names}")
        logging.info(f"🔗 搜索链接：{zh_url}")
        logging.info(f"🔗 备用链接：{en_url}")

        # 使用 Accept-Language 头部来确保获取中文数据
        headers = {"Accept-Language": "zh-CN"}
        zh_resp, en_resp = await asyncio.gather(session.get(zh_url, headers=headers),
                                                session.get(en_url))

        zh_data = await zh_resp.json()
        en_data = await en_resp.json()
        #logging.debug("debug用zh_data\n", zh_data)

    app_id = str(app_id)
    zh_info = zh_data.get(str(app_id), {}).get("data", {}) if zh_data.get(
        str(app_id), {}).get("success") else {}
    en_info = en_data.get(str(app_id), {}).get("data", {}) if en_data.get(
        str(app_id), {}).get("success") else {}
    if not zh_data.get(str(app_id), {}).get("success"):
        logging.error("❗ 中文 API 获取失败")
    if not en_data.get(str(app_id), {}).get("success"):
        logging.error("❗ 英文 API 获取失败")

    # 4. 构建 Embed 优先中文
    display_zh_name = zh_info.get("name") or zh_name or "未知游戏"
    display_en_name = en_info.get("name") or en_name or "Unknown"
    desc = zh_info.get("short_description") or en_info.get(
        "short_description") or "暂无简介"
    
    logging.info(f"✅ zh short_description: {zh_info.get('short_description')}")
    logging.info(f"✅ en short_description: {en_info.get('short_description')}")
    
    header = zh_info.get("header_image") or en_info.get("header_image")
    store_url = f"https://store.steampowered.com/app/{app_id}"
    price_info = zh_info.get("price_overview") or en_info.get("price_overview")

    logging.info(f"🎮 游戏名称：{display_zh_name} / {display_en_name}")
    logging.info(f"🔗 商店链接：{store_url}")
    logging.info(f"🌐 地区：{region_code}")

    if price_info:
        currency = price_info["currency"]
        final = price_info["final"] / 100
        initial = price_info["initial"] / 100
        discount = price_info["discount_percent"]

        if discount > 0:
            price_text = (
                f"现价：{final:.2f} {currency}（原价：{initial:.2f}，折扣：**{discount}%**）"
            )
        else:
            price_text = f"价格：{final:.2f} {currency}"
    else:
        price_text = "免费或暂无价格信息"

    # 构建 Embed 
    embed = Embed(title=f"🎮 {display_zh_name} / {display_en_name}",
                  description=desc,
                  url=store_url)
    embed.add_field(name=f"💰 当前价格 💰 {region_display}",
                    value=price_text,
                    inline=False)
    embed.add_field(name="🔗 商店链接", value=store_url, inline=False)
    if header:
        embed.set_image(url=header)
    else:
        embed.set_image(
            url=
            "https://store.cloudflare.steamstatic.com/public/shared/images/header/globalheader_logo.png"
        )

    await interaction.followup.send(embed=embed)

# ============================== #
# /aww 指令： 随机获取reddit上的可爱动物
# ============================== #
# 初始化 Reddit 客户端的函数
async def get_reddit():
    return asyncpraw.Reddit(
        client_id=os.environ.get("REDDIT_CLIENT_ID"),
        client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
        user_agent=os.environ.get("REDDIT_USER_AGENT"),
    )

# 检验URL是否有效
def is_valid_url(url: str) -> bool:
    return isinstance(url, str) and url.startswith("http")

CUTE_SUBREDDITS = [
    "AnimalsBeingDerps", "AnimalsOnReddit", "aww", "Awww", "Birding", "birdwatching", "BirdsArentReal", "Catmemes", "Eyebleach", "Floof", "Ornithology", "parrots", "PartyParrot", "rarepuppers"
]

# 用于下拉选项
subreddit_choices = [
    app_commands.Choice(name=sub, value=sub) for sub in CUTE_SUBREDDITS
]

@bot.tree.command(name="aww", description="从Reddit上随机抽一只可爱动物")
@app_commands.describe(subreddit="选择subreddit来源，不填则随机")
@app_commands.choices(subreddit=subreddit_choices)
async def aww(interaction: discord.Interaction, subreddit: Optional[app_commands.Choice[str]] = None):
    await interaction.response.defer()

    # 调用初始化 Reddit 客户端的函数
    reddit = await get_reddit()
    
    posts = []
    # 根据用户选择或随机选一个 subreddit
    subreddit_name = subreddit.value if subreddit else random.choice(CUTE_SUBREDDITS)
    subreddit_obj = await reddit.subreddit(subreddit_name)

    # 获取前 50 条热门帖子，包含图片和视频
    async for post in subreddit_obj.hot(limit=50):
        if post.stickied:
            continue

        # 图片链接
        if post.url.endswith((".jpg", ".jpeg", ".png", ".gif")):
            posts.append(post)

        # Reddit 原生视频（非外链）
        elif post.is_video and isinstance(post.media, dict) and "reddit_video" in post.media:
            posts.append(post)

        # gifv（Imgur 或 Gfycat）
        elif post.url.endswith((".mp4", ".webm", ".gifv")):
            posts.append(post)

    logging.info(f"🔍 从 r/{subreddit_name} 获取 {len(posts)} 条图片/视频帖子")

    if not posts:
        await interaction.followup.send("没找到合适的结果捏TT，请稍后再试。")
        return

    selected_post = random.choice(posts)
    
    title = selected_post.title
    if len(title) > 256:
        title = title[:253] + "..."

    embed = discord.Embed(
        title=title,
        url=f"https://reddit.com{selected_post.permalink}",
        description=f"From r/{subreddit_name}",
    )
    
    # 如果是图片或 gif
    if selected_post.url.endswith((".jpg", ".jpeg", ".png", ".gif")):
        if is_valid_url(selected_post.url):
            embed.set_image(url=selected_post.url)
        logging.info(f"🐾 图片链接：{selected_post.url}")

    # 如果是 Reddit 原生视频
    elif (selected_post.is_video and selected_post.media and isinstance(selected_post.media, dict) and "reddit_video" in selected_post.media):
        thumbnail_url = selected_post.thumbnail  # 获取缩略图
        if is_valid_url(thumbnail_url):
            embed.set_image(url=thumbnail_url)
        video_url = selected_post.media["reddit_video"]["fallback_url"]
        embed.description = (embed.description or "") + f"\n[🐾 Click to watch / 点我看视频捏 🐾]({video_url})" + "\n注意：有些 Reddit 视频在这里播放没有声音哦，可以点标题查看原贴>.<"
        logging.info(f"🐾 视频链接：{video_url}")

    # 如果是 mp4/webm
    elif selected_post.url.endswith((".mp4", ".webm")):
        thumbnail_url = selected_post.thumbnail  # 获取缩略图
        if is_valid_url(thumbnail_url):
            embed.set_image(url=thumbnail_url)
        embed.description = (embed.description or "") + f"\n[🐾 Click to watch / 点我看视频捏 🐾]({selected_post.url})" + "\n注意：有些 Reddit 视频在这里播放没有声音哦，可以点标题查看原贴>.<"
        logging.info(f"🐾 mp4/webm链接：{selected_post.url}")
    
    elif selected_post.url.endswith(".gifv"):
        thumbnail_url = selected_post.thumbnail  # 获取缩略图
        if is_valid_url(thumbnail_url):
            embed.set_image(url=thumbnail_url)
        mp4_url = selected_post.url.replace(".gifv", ".mp4")
        embed.description = (embed.description or "") + f"\n[🐾 Click to watch / 点我看视频捏 🐾]({mp4_url})" + "\n注意：有些 Reddit 视频在这里播放没有声音哦，可以点标题查看原贴>.<"
        logging.info(f"🐾 gifv转mp4链接：{mp4_url}")

    logging.info(f"🐾 随机抽取了 r/{subreddit_name} 的帖子：{title} ")
    
    await reddit.close()
    await interaction.followup.send(embed=embed)

# ============================== #
# summary 指令
# ============================== #
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
            "请你总结用户和GPT之间从头到尾的所有历史对话，用于后续对话的 context 使用。请使用第三人称、概括性语言，不要重复原话，不要加入评论或判断。重点总结用户的行为特征、情绪倾向、风格偏好和主要话题。\n"
            },
            {
            "role": "user",
            "content": f"以下是完整的对话历史：\n\n{history_text}"
            }
        ]
        
        #logging.info(f"摘要内容：{summary_prompt}")

        summary_response = await gpt_call(
            model="gpt-4.1",
            messages=summary_prompt,
            temperature=0.3,
            max_tokens=1000,
            timeout=60,
        )

        summary_text = summary_response.choices[0].message.content or ""
        
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
@bot.tree.command(name="summarycheck", description="查看你的对话摘要")
async def summarycheck(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    summary_text = user_summaries.get(user_id)

    if summary_text:
        await interaction.response.send_message(
            f"📄 这是你的对话摘要：\n\n{summary_text}", ephemeral=True)
    else:
        await interaction.response.send_message("ℹ️ 当前还没有摘要哦！", ephemeral=True)


# ============================== #
# rest 指令
# ============================== #
@bot.tree.command(name="reset", description="重置清空所有历史")
async def reset(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_histories.pop(user_id, None)
    user_summaries.pop(user_id, None)
    user_roles.pop(user_id, None)
    save_histories()
    save_summaries()
    save_roles()
    await interaction.response.send_message("✅ 你的历史已清空～可以开始新的提问啦！", ephemeral=True)
    
    logging.info(f"✅ 用户 {user_id} 重置清空了所有历史")
    

# ============================== #
# changestatus 指令
# ============================== #
OWNER_ID = 666250534541328395

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
        
        # 保存设置到本地文件
        with open("status_config.json", "w", encoding="utf-8") as f:
            json.dump({
                "status": online_status.value,
                "activity_type": activity_type.value if activity_type else "",
                "text": text or ""
            }, f, ensure_ascii=False, indent=2)
        
        logging.info(f"🟢 状态已更改为 {online_status.value}" + (f" / {activity_type.value}：{text}" if activity_type and text else ""))
        
    except Exception as e:
        await interaction.response.send_message(f"❌ 出错了：{str(e)}", ephemeral=True)


# ============================== #
# trigger 指令
# ============================== #
@bot.tree.command(name="trigger", description="开启或关闭你的发言自动触发'咋办'")
@app_commands.describe(mode="开启或关闭你的发言自动触发咋办（on/off）")
@app_commands.choices(mode=[
    app_commands.Choice(name="开启 / on", value="on"),
    app_commands.Choice(name="关闭 / off", value="off")
])
async def trigger_control(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    user_id = str(interaction.user.id)
    
    if mode.value == "off":
        disabled_triggers.add(user_id)
        save_triggers_off()
        await interaction.response.send_message("😶 已关闭自动触发`咋办` >.<", ephemeral=True)
    else:
        if user_id in disabled_triggers:
            disabled_triggers.remove(user_id)
            save_triggers_off()
        await interaction.response.send_message("😮 已开启自动触发`咋办` >.<", ephemeral=True)
    
    logging.info(f"🛠 用户 {user_id} 设置触发状态为 {mode.value}")

# ============================== #
# buymeacoffee 指令
# ============================== #
@bot.tree.command(name="buymeacoffee", description="喜欢我可以请作者喝杯咖啡哦 :3c")
async def buymeacoffee(interaction: discord.Interaction):
    embed = discord.Embed(
        title="☕️ Buy Me A Coffee ☕️ 请我喝杯咖啡吧 :3c",
        description="如果你喜欢 咋办 bot 或者被逗笑了一点点，\n可以点击标题通过 ko-fi 请我喝杯咖啡捏！☕️",
        url="https://ko-fi.com/kuroniko07",
        color=0xfefefe
    )
    embed.set_image(url="https://storage.ko-fi.com/cdn/kofi1.png?v=3") 
    embed.set_footer(text="🌈 咋办 bot 目前由一人开发，运行在 VPS 服务器上。\n🌈 相关指令使用的都是 GPT-4.1 模型。\n✨ 谢谢你喜欢咋办 >.< 有任何建议或反馈，也欢迎随时告诉我！\n💌 DM @kuroniko0707")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================== #
# help 指令
# ============================== #
@bot.tree.command(name="help", description="列出所有可用指令")
async def help_command(interaction: discord.Interaction):
    msg = ("可用指令列表：\n"
           "💬 `/ask <问题>` - 咋办\n"
           "💭 `/choose <选项1> <选项2> ...` - 让咋办帮忙选选\n"
           "🔮 `/tarot <困惑>` - 抽一张塔罗牌解读你的困惑\n"
           "🧙‍♀️ `/fortune` - 占卜你的今日运势并解读\n"
           "🐾 `/aww <subreddit>` - 从Reddit上随机抽一只可爱动物\n"
           "🎮 `/steam <游戏名称> [地区]` - 查询 Steam 游戏信息\n"
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
    await interaction.response.send_message(msg)


# ============================== #
# 启动bot
# ============================== #
load_histories()
load_summaries()
load_roles()
load_triggers_off()
bot.run(TOKEN)