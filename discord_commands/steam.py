import asyncio
import logging
import aiohttp
import re
from discord.ext import commands
from discord import Interaction, Embed, app_commands, Color
from typing import Optional
from utils.gpt_call import gpt_call
from utils.embed import get_random_embed_color
from utils.constants import DEFAULT_MODEL

# ============================== #
# /steam 指令
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
    try:
        # 调用现有的 gpt_call
        response = await gpt_call(model=DEFAULT_MODEL,
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
    except Exception as e:
        logging.exception("❌ GPT 获取标准游戏名失败")
        return None


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

def setup(bot: commands.Bot) -> None:
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

            # 3. 获取游戏详情，默认cn
            zh_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=cn&l=zh"
            en_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc={region_code}&l=en"
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
        price_info = en_info.get("price_overview") or zh_info.get("price_overview")

        logging.info(f"🎮 游戏名称：{display_zh_name} / {display_en_name}")
        logging.info(f"🔗 商店链接：{store_url}")
        logging.info(f"🌐 地区：{region_code}")

        if price_info:
            currency = price_info["currency"]
            final = price_info["final"] / 100
            initial = price_info["initial"] / 100
            discount = price_info["discount_percent"]

            if discount > 0:
                discount_amount = initial - final  # 计算减免金额
                price_text = (
                    f"现价: {final:.2f} {currency}\n原价: {initial:.2f} {currency}（已减免 **{discount}%**"
                    f"，优惠了 **{discount_amount:.2f} {currency}**）"
                )
            else:
                price_text = f"价格：{final:.2f} {currency}"
                
            # 设置颜色
            embed_color = get_random_embed_color()
            
        else:
            price_text = "免费或暂无价格信息"
            embed_color = Color.default()

        # 构建 Embed 
        embed = Embed(title=f"🎮 {display_zh_name} / {display_en_name}",
                    description=desc,
                    color=embed_color, )
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