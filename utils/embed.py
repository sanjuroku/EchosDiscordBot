import random
from discord import Color

# ============================== #
# 获取随机RGB颜色函数
# ============================== #
# 获取一个随机的 RGB Embed 颜色（避免太暗的颜色和默认灰）
def get_random_embed_color():
    while True:
        r = random.randint(80, 255)
        g = random.randint(80, 255)
        b = random.randint(80, 255)
        # 避免颜色过暗或接近 Discord 默认灰色
        if (r, g, b) != (54, 57, 63):
            return Color.from_rgb(r, g, b)