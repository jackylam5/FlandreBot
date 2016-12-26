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

    @commands.command(pass_context = True, no_pm = True)
    async def getinfo(self, ctx):
        ''' Get users Stats '''
        message = ctx.message

        if len(message.mentions) == 0:
            user = message.author
        else:
            user = message.mentions[0]

        # Get users last sent message
        messages = self.bot.messages
        messages.reverse()
        last_message = discord.utils.get(messages, author__id=user.id)
        del messages

        # Get users top role
        if user.top_role.name == '@everyone':
            role = user.top_role.name[1:]
        else:
            role = user.top_role.name

        embedcolour = discord.Colour(65535)
        userembed = discord.Embed(type='rich', colour=embedcolour)
        userembed.add_field(name='Name', value=user.name)
        userembed.add_field(name='ID', value=user.id)

        # Check for nickname
        if user.nick is not None:
            userembed.add_field(name='Nickname', value=user.nick)

        userembed.add_field(name='Created', value=user.created_at)
        userembed.add_field(name='Joined', value=user.joined_at)

        # Check voice channel
        if user.voice.voice_channel is not None:
            userembed.add_field(name='Voice Channel', value=user.voice.voice_channel.name)

        # Get Users roles
        roles = [role.name for role in user.roles if role.name != '@everyone']
        if roles:
            userembed.add_field(name='Roles', value=', '.join(roles), inline=False)

        # Check for last message
        if last_message is not None:
            userembed.add_field(name='Last Message', value=last_message.content, inline=False)

        # Set users avatar
        userembed.set_thumbnail(url=user.avatar_url)

        await self.bot.say(embed=userembed)

            

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
