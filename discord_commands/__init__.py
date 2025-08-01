from discord_commands import ask, change_status, choose, role, tarot, fortune, steam, timezone, aww, summary, reset, misc

__all__ = ["setup_all"]

def setup_all(bot):
    ask.setup(bot)
    choose.setup(bot)
    role.setup_setrole(bot)
    role.setup_rolecheck(bot)
    role.setup_resetrole(bot)
    tarot.setup(bot)
    fortune.setup(bot)
    timezone.setup(bot)
    steam.setup(bot)
    aww.setup(bot)
    summary.setup_summary(bot)
    summary.setup_summarycheck(bot)
    change_status.setup(bot)
    reset.setup(bot)
    misc.setup_help(bot)
    misc.setup_buymeacoffee(bot)