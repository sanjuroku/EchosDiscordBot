import aiohttp
import logging
import os
from discord.ext import commands
from discord import Interaction, Embed, app_commands, Color
from typing import Optional
from utils.embed import get_random_embed_color

# ============================== #
# /neodb 指令
# ============================== #

# 获取环境变量中的 Token
NEODB_ACCESS_TOKEN = os.environ.get("NEODB_ACCESS_TOKEN") or ""
if not NEODB_ACCESS_TOKEN:
    raise ValueError(
        "环境变量未设置，请设置 NEODB_ACCESS_TOKEN")

media_type_choices = [
    app_commands.Choice(name="图书 Book", value="book"),
    app_commands.Choice(name="电影 Movie", value="movie"),
    app_commands.Choice(name="影剧 TV Series", value="tv"),
    app_commands.Choice(name="音乐 Album", value="album"),
]

NEODB_SEARCH_API = "https://neodb.social/api/catalog/search"

async def neodb_search(title: str, media_type: Optional[str] = None):
    
    params = {"query": title}
    if media_type:
        params["category"] = media_type

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {NEODB_ACCESS_TOKEN}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(NEODB_SEARCH_API, params=params, headers=headers) as resp:
            text = await resp.text()
            logging.info(f"📡 HTTP 状态码: {resp.status}")
            logging.info(f"📝 返回内容: {resp}")

            if resp.status != 200:
                raise Exception(f"NeoDB API 请求失败，状态码: {resp.status}，内容: {text}")

            data = await resp.json()
            return data.get("data", [])

def build_neodb_embed(item) -> Embed:
    title = item.get("title") or "未知标题"
    original_title = item.get("orig_title")
    subtitle = item.get("subtitle")
    # 标题组合
    title_display = f"{title}"
    if subtitle:
        title_display += f"：{subtitle}"
    if original_title and original_title != title:
        title_display += f" / {original_title}"
        
    # 描述
    description = item.get("description") or "暂无简介"
    
    # 拼接完整 URL
    relative_url = item.get("url") or item.get("id", "")
    if relative_url.startswith("/"):
        url = f"https://neodb.social{relative_url}"
    else:
        url = f"https://neodb.social/{relative_url}" if not relative_url.startswith("http") else relative_url

    # 创建 Embed
    embed = Embed(title=f"🌠 {title_display}",
                  description=description[:1000],
                  url=url,
                  color=get_random_embed_color())
    
    # 封面
    cover_url = item.get("cover_image_url")
    if cover_url:
        embed.set_image(url=cover_url)

    fields = [
        ("类型", item.get("category", "未知"), True),
        ("年份", str(item.get("year", "未知")), True),
        ("时长", item.get("duration", "未知"), True),
        ("导演", ", ".join(item.get("director", [])) or "未知", True),
        ("编剧", ", ".join(item.get("playwright", [])) or "未知", True),
        ("演员", ", ".join(item.get("actor", [])[:5]) + "..." if len(item.get("actor", [])) > 5 else ", ".join(item.get("actor", [])) or "未知", False),
        ("评分", f"{item.get('rating', 'N/A')}（{item.get('rating_count', 0)}人评价）", True),
        ("标签", ", ".join(item.get("tags", [])[:6]) + "..." if len(item.get("tags", [])) > 6 else ", ".join(item.get("tags", [])) or "暂无", False),
        ("IMDb", f"[{item['imdb']}](https://www.imdb.com/title/{item['imdb']})" if item.get("imdb") else "无", True),
    ]

    for name, value, inline in fields:
        if value and value != "未知":
            embed.add_field(name=name, value=value, inline=inline)

    return embed

def setup(bot: commands.Bot) -> None:
    @bot.tree.command(name="neodb", description="查询书影音信息")
    @app_commands.describe(
        title="名称",
        media_type="可选：指定媒体类型"
    )
    @app_commands.choices(media_type=media_type_choices)
    async def neodb(interaction: Interaction,
                    title: str,
                    media_type: Optional[app_commands.Choice[str]] = None):

        await interaction.response.defer()
        
        logging.info(f"用户 {interaction.user.id} 查询 NeoDB: {title} ({media_type.value if media_type else '全部类型'})")
        
        try:
            results = await neodb_search(title, media_type.value if media_type else None)
            
            logging.info(f"NeoDB 查询结果数量: {len(results)}")
            logging.info(f"查询关键词: {title}, 媒体类型: {media_type.value if media_type else '全部类型'}")
            
            if not results:
                await interaction.followup.send("❌ 未找到相关结果，请检查关键词是否正确。", ephemeral=True)
                return

            top_result = results[0]
            embed = build_neodb_embed(top_result)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logging.exception("❌ NeoDB 查询失败：")
            await interaction.followup.send("❌ 查询失败，请稍后再试。", ephemeral=True)