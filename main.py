# ============================== #
# 模块导入与初始化
# ============================== #
import os
import json
import discord
import random
import asyncio
import pytz
from discord.ext import commands
from openai import OpenAI
from keep_alive import keep_alive  # 后面加的保持在线功能
from openai.types.chat import ChatCompletionMessageParam
from datetime import datetime

# 获取环境变量中的 Token
TOKEN = os.environ.get("DISCORD_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if TOKEN is None or OPENAI_API_KEY is None:
    raise ValueError(
        "❌ 环境变量未设置，请在 Replit 的 Secrets 中添加 DISCORD_TOKEN 和 OPENAI_API_KEY")

# 添加锁管理器
user_locks: dict[str, asyncio.Lock] = {}


# gpt_call
async def gpt_call(*args, **kwargs):

    def sync_call():
        return client.chat.completions.create(*args, **kwargs)

    return await asyncio.to_thread(sync_call)


# 初始化 Discord bot
intents = discord.Intents.default()
intents.message_content = True  # 如果需要读取消息内容
intents.members = True  # 如果需要读取成员列表或状态
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
DEFAULT_SYSTEM_PROMPT = "你是一个温柔、聪明、擅长倾听的 AI 小助手。请你认真回答用户的问题。默认用户都为女性，使用女性代称，不使用女性歧视的词语，禁止称呼用户小仙女、小姐姐。如果你不知道答案，请诚实地回答不知道，不要编造内容。你的语言风格亲切可爱，可以在聊天中加点轻松的颜文字、emoji表情。以及当用户说“咋办”的时候只能回复“咋办”两个字，不准加任何的符号或者句子。回复内容不要太啰嗦，保证在1000字以内。"


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
        print("❌ 保存历史记录出错：", e)


def load_histories():
    """从文件加载用户历史记录"""
    global user_histories
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                user_histories = json.load(f)
            print(f"✅ 已从 {HISTORY_FILE} 加载历史记录，共 {len(user_histories)} 个用户")
        except Exception as e:
            print("⚠️ 读取历史记录失败，已忽略：", e)
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
    except Exception as e:
        print("❌ 保存摘要失败：", e)


def load_summaries():
    """加载用户摘要数据"""
    global user_summaries
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
                user_summaries = json.load(f)
            print(f"📄 已从 {SUMMARY_FILE} 加载摘要，共 {len(user_summaries)} 个用户")
        except Exception as e:
            print("⚠️ 摘要读取失败，已忽略：", e)
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
        print(f"📄 正在为用户 {user_id} 生成摘要...")
        print(f"🧠 摘要开始前的历史内容：{len(history)}")

        summary_prompt = [{
            "role":
            "system",
            "content":
            "你是一个AI对话助手，任务是将以下所有从头到尾的JSON历史对话总结为简洁、清楚的背景信息，以便在未来对话中作为 context 使用，不要包含具体提问或回答，仅保留重要背景和用户偏好："
        }, *history]

        #print(summary_prompt)

        #summary_response = client.chat.completions.create(
        summary_response = await gpt_call(
            model="gpt-4.1-mini",
            messages=summary_prompt,
            temperature=0.3,
            max_tokens=500,
            timeout=60,
        )

        summary_text = summary_response.choices[0].message.content or ""
        user_summaries[user_id] = summary_text
        await asyncio.to_thread(save_summaries)
        print(f"✅ 用户 {user_id} 摘要完成")

        # 清除早期对话，只保留最后 50 条
        preserved = history[-50:]
        user_histories[user_id] = preserved
        save_histories()

        print(f"🧹 用户 {user_id} 的历史已清理，仅保留最近 {len(preserved)} 条对话")

    except Exception as e:
        print(f"⚠️ 为用户 {user_id} 生成摘要失败：", e)


# ============================== #
# 角色设定持久化函数
# ============================== #
def save_roles():
    """保存用户角色设定"""
    try:
        with open(ROLE_FILE, "w", encoding="utf-8") as f:
            json.dump(user_roles, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("❌ 保存 role 失败：", e)


def load_roles():
    """加载用户角色设定"""
    global user_roles
    if os.path.exists(ROLE_FILE):
        try:
            with open(ROLE_FILE, "r", encoding="utf-8") as f:
                user_roles = json.load(f)
            print(f"📄 已从 {ROLE_FILE} 加载用户 role，共 {len(user_roles)} 个")
        except Exception as e:
            print("⚠️ 读取 role 失败，已忽略：", e)
            user_roles = {}
    else:
        user_roles = {}


# ============================== #
# bot 启动
# ============================== #
@bot.event
async def on_ready():
    try:
        # 设置状态和活动
        activity = discord.CustomActivity(name="咋办")
        await bot.change_presence(status=discord.Status.online,
                                  activity=activity)

        synced = await bot.tree.sync()
        print(f"✅ Slash commands synced: {len(synced)} 个指令已注册")
    except Exception as e:
        print(e)
    print(f"🤖 已登录为 {bot.user}")


# ============================== #
# ask 指令
# ============================== #
@bot.tree.command(name="ask", description="向 GPT 提问")
async def ask(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()  # 先回个“处理中”
    user_id = str(interaction.user.id)
    lock = get_user_lock(user_id)

    async with lock:
        # 获取历史记录
        history = user_histories.get(user_id, [])
        history.append({"role": "user", "content": prompt})

        # 裁剪用于聊天上下文
        chat_context = history[-MAX_HISTORY:]

        # 如果历史太长则先摘要
        # if len(history) >= SUMMARY_TRIGGER:
        #summarize_history(user_id)
        #history = history[-MAX_HISTORY:]
        #user_histories[user_id] = history

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
                model="gpt-4.1-mini",
                messages=messages,  # 调用包含摘要的完整消息
                temperature=0.7,
                max_tokens=1000,
                timeout=60,
            )
            print(f"模型调用成功：{response.model}")
            print(f"用户提问：{prompt}")

            reply = response.choices[0].message.content or "GPT 没有返回内容。"

            # 添加 AI 回复到历史
            history.append({"role": "assistant", "content": reply})

            # 限制历史长度 & 保存
            user_histories[user_id] = history
            save_histories()

            # 如果历史太长则先摘要
            if len(history) >= SUMMARY_TRIGGER:
                print("🔍 当前完整历史：", len(user_histories[user_id]))
                await summarize_history(user_id)

            await interaction.followup.send(reply)
            print(f"✅ 回复已发送给用户 {user_id}，当前历史记录条数: {len(history)}")

        except Exception as e:
            print("❌ GPT调用出错：", e)
            await interaction.followup.send(f"❌ 出错了：{str(e)}")


# ============================== #
# setrole 指令
# ============================== #
@bot.tree.command(name="setrole", description="设置专属的角色风格")
async def setrole(interaction: discord.Interaction, prompt: str):
    user_id = str(interaction.user.id)
    user_roles[user_id] = prompt
    save_roles()
    await interaction.response.send_message("✅ 角色设定保存了喵！")


# ============================== #
# rolecheck 指令
# ============================== #
@bot.tree.command(name="rolecheck", description="查看你的角色设定")
async def rolecheck(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    prompt = user_roles.get(user_id)
    if prompt:
        await interaction.response.send_message(f"📝 你的当前角色设定是：\n\n{prompt}")
    else:
        await interaction.response.send_message("ℹ️ 你还没有设置自定义角色设定，正在使用默认设定喵～")


# ============================== #
# resetrole 指令
# ============================== #
@bot.tree.command(name="resetrole", description="清除角色风格设定")
async def resetrole(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in user_roles:
        user_roles.pop(user_id)
        save_roles()
        await interaction.response.send_message("✅ 已清除你的自定义角色设定，恢复默认风格喵！")
    else:
        await interaction.response.send_message("ℹ️ 你还没有设置过角色风格哦，当前使用的就是默认设定～")


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


@bot.tree.command(name="tarot", description="让GPT抽一张塔罗牌解读你的困惑")
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
        #response = client.chat.completions.create(
        response = await gpt_call(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.8,
            max_tokens=1000,
            timeout=60,
        )
        print(f"模型调用成功：{response.model}")
        print(f"用户提问：{prompt}")
        reply = response.choices[0].message.content or "GPT 没有返回内容。"
        await interaction.followup.send(f"你抽到的牌是：**{card_name}（{position}）**\n"
                                        f"你的困惑是：**{wish_text}**\n\n"
                                        f"{reply}")

    except Exception as e:
        await interaction.followup.send(f"❌ 出错了：{str(e)}")


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

    prompt = f"""你是一个风趣靠谱的女巫，请用轻松诙谐的语气，为我占卜今天的整体运势。可以从多种多样的方面综合评价。根据塔罗（用户抽到的塔罗牌是：{card_name}（{position}）、星座、八卦、随机事件等自由组合方式生成一个完整的今日运势解析。请保证绝对随机，可以很差，也可以很好。"""

    messages: list[ChatCompletionMessageParam] = [{
        "role": "system",
        "content": system_prompt
    }, {
        "role": "user",
        "content": prompt
    }]

    try:
        #response = client.chat.completions.create(
        response = await gpt_call(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.9,
            max_tokens=1000,
            timeout=60,
        )
        print(f"模型调用成功：{response.model}")
        print(f"用户提问：{prompt}")
        reply = response.choices[0].message.content or "GPT 没有返回内容。"
        await interaction.followup.send(reply)
    except Exception as e:
        await interaction.followup.send(f"❌ 出错了：{str(e)}")


# ============================== #
# timezone 指令
# ============================== #
@bot.tree.command(name="timezone", description="显示当前时间与全球多个时区的对照")
async def timezone(interaction: discord.Interaction):
    await interaction.response.defer()

    # 定义需要展示的时区列表
    timezones = {
        "🇺🇸 美西（洛杉矶）": "America/Los_Angeles",
        "🇺🇸 美中（芝加哥）": "America/Chicago",
        "🇺🇸 美东（纽约）": "America/New_York",
        "🇪🇺 西欧（巴黎）": "Europe/Paris",
        "🇨🇳 中国（北京）": "Asia/Shanghai",
        "🇲🇾 马来西亚": "Asia/Kuala_Lumpur",
        "🇸🇬 新加坡": "Asia/Singapore",
        "🇦🇺 澳大利亚（珀斯）": "Australia/Perth",
        "🇦🇺 澳大利亚（阿德莱德）": "Australia/Adelaide",
        "🇦🇺 澳大利亚（悉尼）": "Australia/Sydney",
        "🇯🇵 日本": "Asia/Tokyo"
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


# ============================== #
# summarycheck 指令
# ============================== #
@bot.tree.command(name="summarycheck", description="查看你的对话摘要")
async def summarycheck(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    summary_text = user_summaries.get(user_id)

    if summary_text:
        await interaction.response.send_message(
            f"📄 这是你的对话摘要：\n\n{summary_text}")
    else:
        await interaction.response.send_message("ℹ️ 当前还没有摘要哦！")


# ============================== #
# rest 指令
# ============================== #
@bot.tree.command(name="reset", description="重置清空GPT历史")
async def reset(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_histories.pop(user_id, None)
    user_summaries.pop(user_id, None)
    user_roles.pop(user_id, None)
    save_histories()
    save_summaries()
    save_roles()
    await interaction.response.send_message("✅ 你的GPT历史已清空～可以开始新的提问啦！")


# ============================== #
# help 指令
# ============================== #
@bot.tree.command(name="help", description="列出所有可用指令")
async def help_command(interaction: discord.Interaction):
    msg = ("可用指令列表：\n"
           "/ask <问题> - 向 GPT 提问\n"
           "/tarot <困惑> - 让GPT抽一张塔罗牌解读你的困惑\n"
           "/fortune - 占卜你的今日运势并解读\n"
           "/timezone - 显示当前时间与全球多个时区的对照\n"
           "/setrole <风格设定> - 设置角色风格\n"
           "/rolecheck - 查看当前角色设定\n"
           "/resetrole - 清除你的角色设定，恢复默认风格\n"
           "/summarycheck - 查看你的对话摘要\n"
           "/reset - 重置清空GPT历史\n"
           "/help - 查看帮助\n")
    await interaction.response.send_message(msg)


# ============================== #
# 启动bot
# ============================== #
load_histories()
load_summaries()
load_roles()
keep_alive()
bot.run(TOKEN)
