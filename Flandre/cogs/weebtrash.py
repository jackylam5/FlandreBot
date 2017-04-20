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
        self.subbed_channels = {}
        self.loaded_config = False
        self.loadConfig()
        if self.loaded_config:
            self.token = ""
            self.token_refresher = self.bot.loop.create_task(self.tokenRefresher())
            self.next_airing = None
            self.next_airing_sender = self.bot.loop.create_task(self.nextAiringSender())

    def loadConfig(self):
        ''' Loads the files for the cogs stored in the cogs data folder
        '''

        if not isdir('Flandre/data/weebtrash'):
            # Make the directory if missing and the files that go with it 
            self.bot.log('warn', 'Cogs data folder not found, it and all files have been made')
            mkdir('Flandre/data/weebtrash')
            with open('Flandre/data/weebtrash/config.json', 'w') as file:
                json.dump({"anilist": {"clientID": "", "clientSecret": ""}}, file, indent=4, sort_keys=True)
            with open('Flandre/data/weebtrash/subbed_channels.json', 'w') as file:
                json.dump({}, file, indent=4, sort_keys=True)
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
            # Check for subbed channels file
            try:
                with open('Flandre/data/weebtrash/subbed_channels.json', 'r') as file:
                    self.subbed_channels = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.subbed_channels = {}
                self.bot.log('error', 'subbed_channels.json could not be loaded. Reason: {0}'.format(e))                
                # Make the file for user again
                with open('Flandre/data/weebtrash/subbed_channels.json', 'w') as file:
                    json.dump({}, file, indent=4, sort_keys=True)
                self.bot.log('info', 'Flandre/data/weebtrash/subbed_channels.json has been remade for you')

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

    async def getAnilistAPIData(self):
        ''' Gets AniList API currently airing anime data and sorts it by next release
        '''

        # Set up request
        request_url = 'https://anilist.co/api/browse/anime'
        params = {'access_token': self.token, 'year': str(datetime.date.today().year),'status': 'Currently Airing', 'airing_data': True}

        # Make request
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(request_url, params=params) as resp:
                status_code = resp.status
                data = await resp.json()

        # Remove any anime that has no airing info due to it being unknown
        for anime in data.copy():
            if anime['airing'] is None:
                data.remove(anime)

        # Sort data so next airing is 1st then the one after and so one
        data = sorted(data, key=lambda k: k['airing'].get('countdown'))
        return data

    async def nextAiringSender(self):
        ''' Gets the next airing episode and posts in subbed channels when it comes out
        '''
        # Wait for token
        await asyncio.sleep(1)
        while True:
            # Grab api data and save the next airing anime
            data = await self.getAnilistAPIData()
            self.next_airing = data[0]
            del data

            # Wait until it airs
            await asyncio.sleep(self.next_airing['airing']['countdown'])

            # Create embed
            em = discord.Embed(type='rich', colour=10057145, description='Episode **{0[airing][next_episode]}** of **{0[title_romaji]} ({0[type]})**'.format(self.next_airing))
            em.set_author(name='Just Released:')
            em.set_thumbnail(url=self.next_airing['image_url_lge'])

            if self.subbed_channel:
                # Send the message saying it is out
                for server, channel in self.subbed_channels.items():
                    subbed_channel = self.bot.get_channel(channel)
                    await self.bot.send_message(subbed_channel, embed=em)

            await asyncio.sleep(1)

    @commands.command(pass_context=True)
    async def airing(self, ctx):
        ''' Gets the current airing anime
        '''
                    
        anime_embed = discord.Embed(type='rich')
        anime_embed.set_author(name='Next Airing:')
        anime_embed.set_thumbnail(url=self.next_airing['image_url_lge'])
        anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})\nKnown as {0[title_english]}'.format(self.next_airing))
        # Get airing time in h,m,s
        m, s = divmod(self.next_airing['airing']['countdown'], 60)
        h, m = divmod(m, 60)
        anime_embed.add_field(name='Episode', value='#**{0[airing][next_episode]}**/**{0[total_episodes]}**\nAirs in: **{1} hours {2} mins**'.format(self.next_airing, h, m))

        await self.bot.send_message(ctx.message.channel, embed=anime_embed) 

    @commands.group(pass_context=True)
    async def airing(self, ctx) :
        ''' Airing anime commands
            airing sub - will make the bot send message when something airs
            No args will make the bot show the next airing anime
        '''
        
        if ctx.invoked_subcommand is None:
            anime_embed = discord.Embed(type='rich', colour=10057145,)
            anime_embed.set_author(name='Next Airing:')
            anime_embed.set_thumbnail(url=self.next_airing['image_url_lge'])
            anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})\nKnown as {0[title_english]}'.format(self.next_airing))
            # Get airing time in h,m,s
            m, s = divmod(self.next_airing['airing']['countdown'], 60)
            h, m = divmod(m, 60)
            anime_embed.add_field(name='Episode', value='#**{0[airing][next_episode]}**/**{0[total_episodes]}**\nAirs in: **{1} hours {2} mins**'.format(self.next_airing, h, m))

            await self.bot.send_message(ctx.message.channel, embed=anime_embed)

    @airing.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def sub(self, ctx):
        ''' Tells bot to use this channel when an anime comes out
            Using it again will remove the channel
        '''

        removed = False
        if ctx.message.server.id in self.subbed_channels:
            self.subbed_channels.pop(ctx.message.server.id)
            removed = True
        else:
            self.subbed_channels[ctx.message.server.id] = ctx.message.channel.id
        
        try:
            with open('Flandre/data/weebtrash/subbed_channels.json', 'w') as file:
                json.dump(self.subbed_channels, file, indent=4, sort_keys=True)
        except:
            if removed:
                await self.bot.say('New releases will no longer be sent to this channel. However it couldn\'t be save for some reason')
            else:
                await self.bot.say('New releases will be sent to this channel. However it couldn\'t be save for some reason')
            self.bot.log('critical', 'Flandre/data/weebtrash/subbed_channels.json could not be saved. Please check it')
        else:
            if removed:
                await self.bot.say('New releases will no longer be sent to this channel.')
                self.bot.log('info', 'Flandre/data/weebtrash/subbed_channels.json has been saved. Reason: {0.name} ({0.id}) has been removed as a subbed channel'.format(ctx.message.channel))
            else:
                await self.bot.say('New releases will be sent to this channel.')
                self.bot.log('info', 'Flandre/data/weebtrash/subbed_channels.json has been saved. Reason: {0.name} ({0.id}) has been made a subbed channel'.format(ctx.message.channel))

def setup(bot):
    n = weebtrash(bot)
    bot.add_cog(n)