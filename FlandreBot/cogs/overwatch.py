import discord
from discord.ext import commands
import aiohttp

class overwatch():
    ''' Get Overwatch information using the Unofficial Overwatch API 
    Found here: https://api.lootbox.eu/documentation
    This API is very slow so please keep that in mind
    '''

    base_url = 'https://api.lootbox.eu'

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["ow"], pass_context=True)
    async def overwatch(self, ctx, platform : str = None, region : str = None, tag : str = None):
        ''' Get user stats e.g !ow <pc,xbl,psn> <eu,us,kr,cn> <tag>
        Defaults to using the first for each
        '''
        platform_list = ['pc', 'xbl', 'psn']
        region_list = ['eu', 'us', 'kr', 'cn']

        if platform is None:
            await self.bot.say("You haven't supplied any arguments!!")
        elif region is None:
            tag = platform
            platform = 'pc'
            region = 'eu'
        elif tag is None:
            if platform not in platform_list:
                tag = region
                region = platform
                platform = 'pc'
                if region not in region_list:
                    region = 'eu'
            else:
                tag = region
                if region not in region_list:
                    region = 'eu'
        else:
            if platform not in platform_list:
                platform = 'pc'
            if region not in region_list:
                region = 'eu'

        if '#' in tag:

            with aiohttp.ClientSession() as aioclient:
                async with aioclient.get(self.base_url + '/{0}/{1}/{2}/profile'.format(platform, region, tag.replace('#', '-'))) as resp:
                    data = await resp.json()
                    status_code = resp.status

            if status_code == 200:
                owembed = discord.Embed(type='rich', colour=16753920)
                owembed.add_field(name='Username', value=data['data']['username'])
                
                level = int(int(data['data']['level']) / 100) * '★' + ' {0} ({1})'.format(str(int(data['data']['level']) % 100), data['data']['level'])
                owembed.add_field(name='Level', value=level)

                msg = 'Wins: {0[games][quick][wins]}\nPlaytime: {0[playtime][quick]}'
                owembed.add_field(name='QuickPlay', value=msg.format(data['data']), inline=False)

                msg = 'Rank: {0[competitive][rank]} SR\nWins: {0[games][competitive][wins]}\nLost: {0[games][competitive][lost]}\nPlayed: {0[games][competitive][played]}\nPlaytime: {0[playtime][competitive]}'
                owembed.add_field(name='Competitive', value=msg.format(data['data']), inline=False)
                owembed.set_thumbnail(url=data['data']['avatar'])

                
                await self.bot.send_message(ctx.message.channel, '{0}, Overwatch info for {1}'.format(ctx.message.author.mention, tag), embed=owembed)
            else:
                await self.bot.say("The API seems to be down right now (Status Code: {0}). Please try again later".format(status_code))
        else:
            await self.bot.say('Invalid Battle tag: {0}'.format(tag))

def setup(bot):
    n = overwatch(bot)
    bot.add_cog(n)