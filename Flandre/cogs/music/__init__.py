from .core import Music

def setup(bot):
    ''' Setup to add cog to bot'''
    cog = Music(bot)
    bot.add_listener(cog.on_voice_state_update, "on_voice_state_update")
    bot.add_cog(cog)