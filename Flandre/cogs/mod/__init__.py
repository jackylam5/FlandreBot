from .core import Mod

def setup(bot):
    ''' Setup for bot to add cog '''
    cog = Mod(bot)
    bot.add_listener(cog.member_ban, "on_member_ban")
    bot.add_listener(cog.member_kick, "on_member_remove")
    bot.add_cog(cog)
