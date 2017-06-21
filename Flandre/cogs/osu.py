''' Holds the osu! cog for the bot '''
import aiohttp
import discord
from discord.ext import commands

from .. import permissions, utils

OSU_MODES = {'0': 'osu!',
             '1': 'Taiko',
             '2': 'CtB',
             '3': 'osu!mania',
            }
OSU_MAP_STATUS = {'-2': 'Graveyard',
                  '-1': 'WIP',
                  '0': 'Pending',
                  '1': 'Ranked',
                  '2': 'Approved',
                  '3': 'Qualified',
                  '4': 'Loved',
                 }
OSU_BASE_URL = 'https://osu.ppy.sh'

class Osu:
    '''
    osu! commands
    If beatmap link is posted bot will send info on that map
    '''

    def __init__(self, bot):
        self.bot = bot
        self.config = utils.check_cog_config(self, 'config.json', default={'api_key': ''})
        self.session = aiohttp.ClientSession()

    def __unload(self):
        ''' Remove listeners and close sessions'''
        self.session.close()

    async def __local_check(self, ctx):
        return utils.check_enabled(ctx)

    async def get_osu_user_info(self, user, mode=0):
        '''
        Makes a request to the osu! api to get user info
        Check OSU_MODES to know what number is for what mode
        '''

        if user:
             # Do nothing rn
             pass
        else:
            return {}


    @commands.group(name='osu')
    @commands.cooldown(60, 60.0, type=commands.BucketType.default)
    async def _osu(self, ctx):
        '''
        osu! commands
        Contains commands for the standard mode
        It also contains a group of commands for the other game mode
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @_osu.command(name='user')
    async def osu_user(self, ctx):
        ''' Show basic user info for standard '''


    @_osu.group(name='mania')
    async def _mania(self, ctx):
        ''' Contains commands for mania '''

        if ctx.subcommand_passed == 'mania':
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

def setup(bot):
    ''' Setup for bot to add cog '''
    cog = Osu(bot)
    bot.add_cog(cog)
