from . import basic_events, trigger_events
from .guild_events import setup_guild_event_handlers

def setup_all(bot):
    basic_events.setup(bot)
    trigger_events.setup(bot)
    setup_guild_event_handlers(bot)