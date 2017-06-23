''' Holds the osu! cog for the bot '''
import re

import aiohttp
import discord
from discord.ext import commands

from .. import permissions, utils

OSU_MODES = {0: 'osu!',
             1: 'Taiko',
             2: 'CtB',
             3: 'osu!mania',
            }
OSU_MAP_STATUS = {-2: 'Graveyard',
                  -1: 'WIP',
                  0: 'Pending',
                  1: 'Ranked',
                  2: 'Approved',
                  3: 'Qualified',
                  4: 'Loved',
                 }
RANK_EMOTES = {'D': '<:Drank:327169368003837953>',
               'C': '<:Crank:327169368578326548>',
               'B': '<:Brank:327169368091918356>',
               'A': '<:Arank:327169368079204352>',
               'S': '<:Srank:327169368272273418>',
               'SH': '<:SHrank:327169368712544256>',
               'X': '<:Xrank:327169369111134209>',
               'XH': '<:XHrank:327169369782091777>',
              }
OSU_BASE_URL = 'https://osu.ppy.sh'

USER_RECENT_REGEX = re.compile(r"<img src='\/images\/([A-Za-z]+)_small\.png'\/>\s*<b>\s*<a href='\/u\/\d+'>([^<]+)<\/a>\s*<\/b>\s*achieved rank #(\d+) on <a href='\/b\/([0-9]+\?m=[0-9])'>([^<]+)<\/a>\s*\(([^\(]+)\)")

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

        if not user:
            return {}

        key = self.config["api_key"]
        url = f'{OSU_BASE_URL}/api/get_user?k={key}&u={user}&m={mode}&event_days=31'
        async with self.session.get(url) as resp:
            data = await resp.json()

        return data[0] if data else {}

    async def get_osu_user_top(self, user, mode=0):
        ''' Gets the users top 5 scores'''

        if not user:
            return {}

        key = self.config["api_key"]
        url = f'{OSU_BASE_URL}/api/get_user_best?k={key}&u={user}&m={mode}&limit=5'
        async with self.session.get(url) as resp:
            data = await resp.json()

        return data if data else {}

    async def get_osu_beatmap(self, beatmap, mode=0):
        ''' Gets beatmap info from the id given '''

        if not beatmap:
            return {}

        key = self.config["api_key"]
        url = f'{OSU_BASE_URL}/api/get_beatmaps?k={key}&b={beatmap}&m={mode}'
        async with self.session.get(url) as resp:
            data = await resp.json()

        return data if data else {}


    def create_user_embed(self, user, mode=0):
        ''' Creates an embed about that user for that mode '''

        # Convert to numbers so they can be formatted nicely
        pp_raw = float(user['pp_raw'])
        pp_rank = int(user['pp_rank'])
        pp_country = int(user['pp_country_rank'])
        acc = float(user['accuracy'])
        level = float(user['level'])
        playcount = int(user['playcount'])
        ranked_score = int(user['ranked_score'])
        total_score = int(user['total_score'])
        flag = f':flag_{user["country"].lower()}:'

        desc = (f'Rank: #{pp_rank:,} ({pp_raw:.2f}pp)\n'
                f'Country Rank: #{pp_country:,} {flag}\n'
                f'Accuracy: {acc:.2f}%\n'
                f'Level: {level:.2f}\n'
                f'Playcount: {playcount:,}\n'
                f'Ranked Score: {ranked_score:,}\n'
                f'Total Score: {total_score:,}')

        title = f'{user["username"]}'
        url = f'{OSU_BASE_URL}u/{user["user_id"]}'
        embed = discord.Embed(description=desc,
                              title=title,
                              url=url,
                              colour=16738740)

        embed.set_author(name=f'User Info ({OSU_MODES[mode]})')
        embed.set_thumbnail(url=f'https://a.ppy.sh/{user["user_id"]}')

        # Add recent score to embed
        if user['events']:
            recent = user['events'][0]['display_html']

            # Find the rank they got
            match = USER_RECENT_REGEX.match(recent)
            if match is not None:
                rank = RANK_EMOTES[match[1]]
                number = match[3]
                beatmap = f'[{match[5]}]({OSU_BASE_URL}/b/{match[4]})'
                mode = match[6]
                embed.add_field(name='Recent:', value=f'{rank} Achieved #{number} on {beatmap} ({mode})')

        return embed

    async def create_top_embed(self, scores, name, mode=0):
        ''' Creates the embed for the top 5 scores '''

        url = f'{OSU_BASE_URL}u/{scores[0]["user_id"]}'

        embed = discord.Embed(title=name, url=url, colour=16738740)
        embed.set_author(name=f'Top Scores ({OSU_MODES[mode]})')
        embed.set_thumbnail(url=f'https://a.ppy.sh/{scores[0]["user_id"]}')

        for score in scores:
            beatmap = await self.get_osu_beatmap(score['beatmap_id'], mode=mode)
            beatmap = beatmap[0]

            title = f'{beatmap["title"]} [{beatmap["version"]}]'
            pp_raw = float(score['pp'])
            total_score = int(score['score'])
            page_link = f'{OSU_BASE_URL}/b/{score["beatmap_id"]}&m={mode}'
            direct_link = f'osu://dl/{beatmap["beatmapset_id"]}'
            if beatmap['max_combo'] is None:
                max_combo = 'x combo'
            else:
                max_combo = f'/{beatmap["max_combo"]} combo'

            info = (f'{RANK_EMOTES[score["rank"]]} '
                    f'**{total_score:,} {pp_raw:.2f}pp** '
                    f'`{score["count300"]}/{score["count100"]}/'
                    f'{score["count50"]}/{score["countmiss"]}` '
                    f'**{score["maxcombo"]}{max_combo}**\n'
                    f'[osu!page]({page_link}) [osu!direct]({direct_link})')

            embed.add_field(name=title, value=info, inline=False)

        return embed

    # Standard mode
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
    async def osu_user(self, ctx, *, name: str):
        ''' Show basic user info for standard '''
        user = await self.get_osu_user_info(name)

        if user:
            embed = self.create_user_embed(user)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

    @_osu.command(name='top')
    @commands.cooldown(1, 10.0, type=commands.BucketType.default)
    async def osu_top(self, ctx, *, name: str):
        ''' Show basic user info for standard '''
        top_scores = await self.get_osu_user_top(name)

        if top_scores:
            embed = await self.create_top_embed(top_scores, name)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

    # Mania
    @_osu.group(name='mania')
    async def _mania(self, ctx):
        ''' Contains commands for mania '''

        if ctx.subcommand_passed == 'mania':
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @_mania.command(name='user')
    async def mania_user(self, ctx, *, name: str):
        ''' Show basic user info for mania '''
        user = await self.get_osu_user_info(name, 3)

        if user:
            embed = self.create_user_embed(user, 3)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

    @_mania.command(name='top')
    @commands.cooldown(1, 10.0, type=commands.BucketType.default)
    async def mania_top(self, ctx, *, name: str):
        ''' Show basic user info for mania '''
        top_scores = await self.get_osu_user_top(name, 3)

        if top_scores:
            embed = await self.create_top_embed(top_scores, name, 3)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

    # Taiko
    @_osu.group(name='taiko')
    async def _taiko(self, ctx):
        ''' Contains commands for taiko '''

        if ctx.subcommand_passed == 'taiko':
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @_taiko.command(name='user')
    async def taiko_user(self, ctx, *, name: str):
        ''' Show basic user info for taiko '''
        user = await self.get_osu_user_info(name, 1)

        if user:
            embed = self.create_user_embed(user, 1)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

    @_taiko.command(name='top')
    @commands.cooldown(1, 10.0, type=commands.BucketType.default)
    async def taiko_top(self, ctx, *, name: str):
        ''' Show basic user info for taiko '''
        top_scores = await self.get_osu_user_top(name, 1)

        if top_scores:
            embed = await self.create_top_embed(top_scores, name, 1)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

    # CtB
    @_osu.group(name='ctb')
    async def _ctb(self, ctx):
        ''' Contains commands for ctb '''

        if ctx.subcommand_passed == 'ctb':
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @_ctb.command(name='user')
    async def ctb_user(self, ctx, *, name: str):
        ''' Show basic user info for ctb '''
        user = await self.get_osu_user_info(name, 2)

        if user:
            embed = self.create_user_embed(user, 2)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

    @_ctb.command(name='top')
    @commands.cooldown(1, 10.0, type=commands.BucketType.default)
    async def ctb_top(self, ctx, *, name: str):
        ''' Show basic user info for ctb '''
        top_scores = await self.get_osu_user_top(name, 2)

        if top_scores:
            embed = await self.create_top_embed(top_scores, name, 2)
            await ctx.send(embed=embed)
        else:
            await ctx.send('I couldn\'t find that user!')

def setup(bot):
    ''' Setup for bot to add cog '''
    cog = Osu(bot)
    bot.add_cog(cog)
