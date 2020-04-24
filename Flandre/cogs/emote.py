''' Holds the emote cog '''
from discord.ext import commands
from .. import permissions, utils


class Emote(commands.Cog):
    ''' Holds commands that don't have a suitable place else where '''
    def __init__(self, bot):
        self.bot = bot
        self.emotes = utils.check_cog_config(self, 'emotes.json')
        self.emote_log = utils.check_cog_config(self, 'emote_log.json')
        self.transparency_emote = '<:transparent:650746475755864064>'

    def __unload(self):
        ''' Remove listeners '''
    
    async def __local_check(self, ctx):
        return utils.check_enabled(ctx)

    @commands.group()
    async def emote(self, ctx):
        '''
        Emote command

        emote add - add emote to list
        emote remove - remove emote from list
        emote show - shows all emotes
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @emote.command()
    @permissions.check_owners()
    async def add(self, ctx, emote: str, text: str):
        '''Add emote to bot'''

        # Check if the emote exist.
        if emote in self.emotes:
            await ctx.send(f"{emote} already exist.")

        else:
            self.emotes[emote] = text
            await ctx.send(f"{emote} added: \n{text}.")

            # Save the json file
            utils.save_cog_config(self, 'emotes.json', self.emotes)

    @emote.command()
    @permissions.check_owners()
    async def remove(self, ctx, emote: str):
        '''Remove emote from bot'''

        # Check if the emote exist.
        if emote in self.emotes:
            self.emotes.pop(emote)
            await ctx.send(f"{emote} removed.")

            # Save the json file
            utils.save_cog_config(self, 'emotes.json', self.emotes)
        else:
            await ctx.send(f"{emote} does not exist.")

    @emote.command()
    async def show(self, ctx):
        '''Show all emotes'''

        await ctx.send(f"{self.emotes}")

    @emote.command()
    async def e(self, ctx, emote: str):
        '''Show emote'''

        # Check if the emote exist.
        if emote in self.emotes:
            await ctx.send(f"{self.transparency_emote}\n{self.emotes[emote]}")

        else:
            await ctx.send(f"{emote} does not exist")

            # Save the json file
            utils.save_cog_config(self, 'emotes.json', self.emotes)

    @emote.command()
    async def test(self, ctx):
        '''check last emote'''
        
        
        async for message in ctx.channel.history(limit=100):
            if '<:' in message.content:
                print("aaa")
                self.emote_log[message.id] = message.content
                break
        

        # Save the json file
        utils.save_cog_config(self, 'emote_log.json', self.emote_log)
        await ctx.send('Done!')



def setup(bot):
    ''' Setup function to add cog to bot '''
    cog = Emote(bot)
    bot.add_cog(cog)
