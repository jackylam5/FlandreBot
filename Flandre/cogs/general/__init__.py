from .core import General

def setup(bot):
    ''' Setup function to add cog to bot '''
    cog = General(bot)
    bot.add_listener(cog.check_poll_votes, "on_message")
    bot.add_cog(cog)
