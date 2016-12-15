import discord
from discord.ext import commands
import os
from FlandreBot.utils.IO import files

class Test:


    def __init__(self, bot):
        self.bot = bot
        self.players = files("FlandreBot/data/players.json", "load")


    @commands.command(hidden=True)
    async def test(self):
        """Pong."""
        await self.bot.say("ok!")
        
    @commands.command(pass_context = True, no_pm = True)
    async def register(self, ctx):
        """Create a new account"""
        
        user = ctx.message.author
        if user.id not in self.players:
            self.players[user.id] = {"name" : user.name, "Scrubs" : 1337}
            files("FlandreBot/data/players.json", "save", self.players)
            await self.bot.say("{}, your account has been created!".format(user.mention))
        else:
            await self.bot.say("{}, you already have an account!".format(user.mention))
            

def check_files():
    if not os.path.exists("FlandreBot/data"):
        os.makedirs("FlandreBot/data")
    
    f = "FlandreBot/data/players.json"
    if not files(f, "check"):
        files(f, "save", {})

def setup(bot):
    check_files()
    n = Test(bot)
    bot.add_cog(n)
