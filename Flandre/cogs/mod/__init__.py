from .core import Mod

def setup(bot):
    ''' Setup for bot to add cog '''
    cog = Mod(bot)
    bot.add_listener(cog.member_ban, "on_member_ban")
    bot.add_listener(cog.member_kick, "on_member_remove")
    bot.add_listener(cog.on_message, "on_message")
    bot.add_listener(cog.on_message_edit, "on_message_edit")
    bot.add_cog(cog)
