import discord
from discord.ext import commands
import asyncio
import aiohttp
import json
import datetime
from operator import itemgetter
from os import mkdir
from os.path import isdir
from Flandre import permissions

class weebtrash:
    ''' Cog that has all anime and manga related items.
        Uses the anilist/mal api to get info about that anime/manga
    '''

    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.loaded_config = False
        self.loadConfig()
        if self.loaded_config:
            self.token = ""
            self.token_refresher = self.bot.loop.create_task(self.tokenRefresher())

    def loadConfig(self):
        ''' Loads the files for the cogs stored in the cogs data folder
        '''

        if not isdir('Flandre/data/weebtrash'):
            # Make the directory if missing and the files that go with it 
            self.bot.log('warn', 'Cogs data folder not found, it and all files have been made')
            mkdir('Flandre/data/weebtrash')
            with open('Flandre/data/weebtrash/config.json', 'w') as file:
                json.dump({"anilist": {"clientID": "", "clientSecret": ""}}, file, indent=4, sort_keys=True)
        else:
            # Check for config file
            try:
                with open('Flandre/data/weebtrash/config.json', 'r') as file:
                    self.config = json.load(file)
                    self.loaded_config = True
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.config = {}
                self.bot.log('error', 'config.json could not be loaded. Reason: {0}'.format(e))                
                # Make the file for user again
                with open('Flandre/data/weebtrash/config.json', 'w') as file:
                    json.dump({"anilist": {"clientID": "", "clientSecret": ""}}, file, indent=4, sort_keys=True)
                self.bot.log('info', 'Flandre/data/weebtrash/config.json has been remade for you')

    async def tokenRefresher(self):
        ''' Background task to refresh anilist api token every hour
        '''
        auth_url = 'https://anilist.co/api/auth/access_token'
        auth_data = {'grant_type': "client_credentials", 'client_id': self.config['anilist']['clientID'], 'client_secret': self.config['anilist']['clientSecret']}
        while True:
            
            with aiohttp.ClientSession() as aioclient:
                async with aioclient.post(auth_url, data=auth_data) as resp:
                    status_code = resp.status
                    data = await resp.json()

            self.token = data['access_token']
            await asyncio.sleep(data['expires_in'])

    @commands.command(pass_context=True)
    async def airing(self, ctx):
        ''' Gets the current airing anime
        '''

        request_url = 'https://anilist.co/api/browse/anime'
        year = datetime.date.today().year
        params = {'access_token': self.token, 'year': str(year),'status': 'Currently Airing', 'airing_data': True}

        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(request_url, params=params) as resp:
                status_code = resp.status
                data = await resp.json()

        if status_code == 200:
            next_airing_data = data.pop(0)

            for anime in data:
                if anime['airing'] is not None:
                    if anime['airing']['countdown'] < next_airing_data['airing']['countdown']:
                        next_airing_data = anime        

            anime_embed = discord.Embed(type='rich')
            anime_embed.set_author(name='Next Airing:')
            anime_embed.set_thumbnail(url=next_airing_data['image_url_lge'])
            anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})\nKnown as {0[title_english]}'.format(next_airing_data))
            # Get airing time in h,m,s
            m, s = divmod(next_airing_data['airing']['countdown'], 60)
            h, m = divmod(m, 60)
            anime_embed.add_field(name='Episode', value='#**{0[airing][next_episode]}**/**{0[total_episodes]}**\nAirs in: **{1} hours {2} mins**'.format(next_airing_data, h, m))

            await self.bot.send_message(ctx.message.channel, embed=anime_embed)        

def setup(bot):
    n = weebtrash(bot)
    bot.add_cog(n)    
            