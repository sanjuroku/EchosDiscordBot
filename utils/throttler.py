from asyncio_throttle.throttler import Throttler

# 每5秒最多5次
throttler = Throttler(rate_limit=5, period=5)

async def send_message(channel, content):
    async with throttler:
        await channel.send(content)