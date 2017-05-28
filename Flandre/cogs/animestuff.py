import discord
from discord.ext import commands
import asyncio
import aiohttp
import json
import datetime
import xml.etree.ElementTree as et
from dateutil.parser import parse
from .. import permissions, utils

class animestuff:
    ''' Cog that has all anime and manga related items.
        Uses the anilist api to get info about that anime/manga
        Works using time in Japan (GMT+9)
    '''

    def __init__(self, bot):
        self.bot = bot
        self.config = utils.checkCogConfig(self, 'config.json', default={"anilist": {"clientID": "", "clientSecret": ""}, "mal": {"username": "", "password": ""}})
        # Variables of subbedchannels, people that want notifs and airing today anime and ids for all airing
        self.subbed_channels = utils.checkCogConfig(self, 'subbed_channels.json', default={'channels': []})
        self.notifications = utils.checkCogConfig(self, 'notifications.json')
        self.airing_today = []
        self.anime_to_be_released = asyncio.Event()
        self.all_airing_ids = {} # Key is anime ID as a string        
        self.token = ""
        self.token_refresher = self.bot.loop.create_task(self.tokenRefresher())
        self.daily_anime_grabber = self.bot.loop.create_task(self.dailyAnimeGrabber())
        self.next_airing_sender = self.bot.loop.create_task(self.nextAiringSender())
        self.hourly_notify = self.bot.loop.create_task(self.hourlyNotifyer())

    def __unload(self):
        ''' Unload function for when it is unloaded
        '''
        # Cancel all background tasks
        self.token_refresher.cancel()
        self.daily_anime_grabber.cancel()
        self.next_airing_sender.cancel()
        self.hourly_notify.cancel()
        self.airing_today = []
        self.all_airing_ids = {}

    async def tokenRefresher(self):
        ''' Background task to refresh anilist api token every hour
        '''
        
        # Set up POST data to get token
        auth_url = 'https://anilist.co/api/auth/access_token'
        auth_data = {'grant_type': "client_credentials", 'client_id': self.config['anilist']['clientID'], 'client_secret': self.config['anilist']['clientSecret']}
        while True:
            
            # Request token
            async with aiohttp.ClientSession() as aioclient:
                async with aioclient.post(auth_url, data=auth_data) as resp:
                    data = await resp.json()


            # Save token and wait untill it expires
            self.token = data['access_token']
            await asyncio.sleep(data['expires_in'])

    async def getAnilistPageInfo(self, aniid):
        ''' Gets page info for anime from ID (Mainly used to get crunchyroll link)
        '''

        # Set up request and params
        request_url = f'https://anilist.co/api/anime/{aniid}/page'
        params = {'access_token': self.token}

        # Make request
        async with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(request_url, params=params) as resp:
                data = await resp.json()

        return data

    async def getMALAnimeInfo(self, anime):
        ''' Get MAL anime info from name
        '''
        # Remove spaces for web request
        anime = anime.replace(' ', '_')

        try:
            # Request Information
            async with aiohttp.ClientSession() as aioclient:
                async with aioclient.get(f'https://myanimelist.net/api/anime/search.xml?q={anime}', auth=aiohttp.BasicAuth(self.config['mal']['username'], self.config['mal']['password'])) as resp:
                    data = await resp.text()
                    data = et.fromstring(data)

            return [i for i in [dict((info.tag, info.text) for info in entrys) for entrys in data]]
        except:
            return []

    async def dailyAnimeGrabber(self):
        ''' Function that does all daily checks and get all anime airing that day
        '''

        # Wait for token before we do anything
        await asyncio.sleep(2)

        while True:

            # Set up request to get all airing anime
            request_url = 'https://anilist.co/api/browse/anime'
            page = 0 # Page number for api request
            page_number_found = 40 # Number of anime found (if < 40 found we have them all)
            year = str(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).year) # Current year
            animes = []

            while page_number_found == 40:
                # Make params                
                params = {'access_token': self.token, 'year': year, 'status': 'Currently Airing', 'airing_data': 'True', 'page': page}
                
                # Make request
                async with aiohttp.ClientSession() as aioclient:
                    async with aioclient.get(request_url, params=params) as resp:
                        data = await resp.json()

                # Add anime found to list, increase page number, and set page_number_found
                animes += data
                page += 1
                page_number_found = len(data)

            # Remove hentai as it has no airing info for some reason
            for anime in animes.copy():
                if anime['airing'] is None:
                    animes.remove(anime)

            # Put all airing animes in a dict with id as key and tuple of titles
            self.all_airing_ids = {str(k['id']): k['title_romaji'] for k in animes}

            # Remove any anime that is no longer airing
            removed_counter = 0 # Remove counter for log
            for notify_id in self.notifications.copy():
                if notify_id not in self.all_airing_ids:
                    self.notifications.pop(notify_id)
                    removed_counter += 1

            # Save notifications.json
            utils.saveCogConfig(self, 'notifications.json', self.notifications)
            self.bot.logger.info("Found {0} currently airing anime. Removed {1} no longer airing anime from notification file".format(len(animes), removed_counter))

            # Get current date and reset airing today
            today = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            midnight_tomorrow = (today + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            self.airing_today = []

            # Get all anime that airs today
            for anime in animes:                
                airdate = parse(anime['airing']['time'])
                # Check if it airs today
                if airdate <= midnight_tomorrow:
                    if anime not in self.airing_today:
                        self.airing_today.append(anime)

            # Check if we have any airing 
            if len(self.airing_today) > 0:

                # Sort anime airing today by the countdown suppied by anilist
                # (Will be wrong when working with it but it tells us what should air first, We will calculate the true time from the time given)
                # If it has aired it will be none but when we get it here it shouldn't be none
                self.airing_today = sorted(self.airing_today, key=lambda x: (x['airing']['countdown'] is None, x['airing'].get('countdown')))

                # Tell the airing background task that there is anime airing today
                self.anime_to_be_released.set()
                
                # Make an embed to tell users what airs today
                desc = ''
                for anime in self.airing_today:                    
                    # Get total eps formated nicely
                    total_ep = int(anime['total_episodes'])
                    if total_ep == 0:
                        total_ep = '-'
                    desc += '[ID: {0[id]}] {0[title_romaji]} [{0[airing][next_episode]}/{1}]\n'.format(anime, total_ep)

                timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
                em = discord.Embed(type='rich', colour=10057145, description=desc, timestamp=timestamp)
                em.set_author(name='Airing today:')
                em.set_footer(text='Info from Anilist', icon_url='https://anilist.co/img/logo_al.png')

                # Send Embed
                if len(self.subbed_channels) > 0:
                    for channel in self.subbed_channels['channels']:
                        subbed_channel = self.bot.get_channel(channel)
                        await subbed_channel.send(embed=em)

            # Wait for the next day
            next_day = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) + datetime.timedelta(days=1)
            time_left = next_day.replace(hour=0, minute=2, second=0, microsecond=0) - datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            await asyncio.sleep(round(time_left.total_seconds()))

    async def nextAiringSender(self):
        ''' Gets the next airing episode and posts in subbed channels when it comes out
        '''
        # Wait for token
        await asyncio.sleep(1)
        while True:
            await self.anime_to_be_released.wait()
            self.anime_to_be_released.clear()
            
            # Recalculate countdown
            time_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            for i, anime in enumerate(self.airing_today.copy()):
                if anime['airing']['countdown'] != None:
                    countdown = parse(anime['airing']['time']) - time_now
                    self.airing_today[i]['airing']['countdown'] = round(countdown.total_seconds())

            self.airing_today = sorted(self.airing_today, key=lambda x: (x['airing']['countdown'] is None, x['airing'].get('countdown')))

            # If first element counntdown is none all has aired
            if self.airing_today[0]['airing']['countdown'] != None:
                await asyncio.sleep(self.airing_today[0]['airing']['countdown'])

                # Get anime page info for crunchyroll link
                page_info = await self.getAnilistPageInfo(self.airing_today[0]['id'])
                cr_link = ''

                for link in page_info['external_links']:
                    if link['site'].lower() == 'crunchyroll':
                        cr_link = link['url']
                        break

                # Get MAL link
                mal_data = await self.getMALAnimeInfo(self.airing_today[0]['title_romaji'])

                # Create embed
                timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
                em = discord.Embed(type='rich', colour=10057145, description='Episode **{0[airing][next_episode]}** of **{0[title_romaji]} ({0[type]})**'.format(self.airing_today[0]), timestamp=timestamp)
                em.set_author(name='Just Released:')
                # Add crunchyroll link to embed if it was found
                if cr_link != '':
                    em.description += '\nWatch on [Crunchyroll]({0})'.format(cr_link)
                em.set_thumbnail(url=self.airing_today[0]['image_url_lge'])
                # Add links to embed
                links = '[Anilist](https://anilist.co/anime/{0})'.format(self.airing_today[0]['id'])
                if len(mal_data) > 0:
                    links += ' [MAL](https://myanimelist.net/anime/{0})'.format(mal_data[0]['id'])
                em.add_field(name='Links:', value=links)
                em.add_field(name='DM Notification:', value='Type **@{0} anime notify {1}** to get DM notifications for this anime'.format(self.bot.user.name, self.airing_today[0]['id']))
                em.set_footer(text='Info from Anilist', icon_url='https://anilist.co/img/logo_al.png')

                # Send Embed
                if len(self.subbed_channels) > 0:
                    for channel in self.subbed_channels['channels']:
                        subbed_channel = self.bot.get_channel(channel)
                        await subbed_channel.send(embed=em)

                if str(self.airing_today[0]['id']) in self.notifications:
                    for user_id in self.notifications[str(self.airing_today[0]['id'])]:
                        try:
                            user = self.bot.get_user(user_id)
                            if user is not None:
                                await user.send(embed=em)
                        except:
                            continue

                self.airing_today[0]['airing']['countdown'] = None
            
            all_aired = True
            for anime in self.airing_today:
                if anime['airing']['countdown'] != None:
                    all_aired = False
                    break

            if all_aired == False:        
                self.anime_to_be_released.set()

    async def hourlyNotifyer(self):
        ''' Checks every hour (on the hour) and post if anything is airing in that hour 
        '''
        
        # Wait for the next exact hour
        next_hour = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) + datetime.timedelta(hours=1)
        time_left = next_hour.replace(minute=0, second=0, microsecond=0) - datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        await asyncio.sleep(round(time_left.total_seconds()))

        while True:
            airing_soon = []
            time_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            # Get all anime airing within the hour seconds <= 3660 but more that a min away
            for anime in self.airing_today:
                if anime['airing']['countdown'] != None:
                    countdown = parse(anime['airing']['time']) - time_now
                    if round(countdown.total_seconds()) <= 3660 and round(countdown.total_seconds()) > 60:
                        airing_soon.append(anime)

            # Check if there are any airing soon
            if len(airing_soon) > 0:
                # Create description
                desc = ''
                for i, anime in enumerate(airing_soon):
                    countdown = parse(anime['airing']['time']) - datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
                    # Tidy up if unknown eps
                    total_ep = int(anime['total_episodes'])
                    if total_ep == 0:
                        total_ep = '-'
                    desc += '{0}: [{1[title_romaji]}](https://anilist.co/anime/{1[id]}) ({1[type]}) [{1[airing][next_episode]}/{2}] in {3}\n'.format((i+1), anime, total_ep, str(countdown).split('.')[0])
                
                # Create embed
                timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
                em = discord.Embed(type='rich', colour=10057145, description=desc, timestamp=timestamp)
                em.set_author(name='Airing within the next hour:')
                em.set_footer(text='Info from Anilist', icon_url='https://anilist.co/img/logo_al.png')

                # Send Embed
                if len(self.subbed_channels) > 0:
                    for channel in self.subbed_channels['channels']:
                        subbed_channel = self.bot.get_channel(channel)
                        await subbed_channel.send(embed=em)

            # Wait for the next exact hour
            next_hour = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) + datetime.timedelta(hours=1)
            time_left = next_hour.replace(minute=0, second=0, microsecond=0) - datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            await asyncio.sleep(round(time_left.total_seconds()))

    @commands.group()
    async def anime(self, ctx) :
        ''' Anime commands 
            Uses AniList and MAL
        '''
        
        if ctx.invoked_subcommand is None:
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @anime.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def sub(self, ctx):
        ''' Tells bot to use this channel when an anime comes out
            Using it again will remove the channel
        '''

        removed = False
        if ctx.channel.id in self.subbed_channels['channels']:
            self.subbed_channels['channels'].remove(ctx.channel.id)
            removed = True
        else:
            self.subbed_channels['channels'].append(ctx.channel.id)
        
        # Save json file
        utils.saveCogConfig(self, 'subbed_channels.json', self.subbed_channels)

        
        if removed:
            await ctx.send('New releases will no longer be sent to this channel.')
            self.bot.logger.info(f'{ctx.channel.name} ({ctx.channel.id}) has been removed as a subbed channel')
        else:
            await ctx.send('New releases will be sent to this channel.')
            self.bot.logger.info(f'{ctx.channel.name} ({ctx.channel.id}) has been made a subbed channel')

    @anime.command(name='next')
    async def anime_next(self, ctx):
        ''' Displays info on the next airing anime
        '''

        next_airing = self.airing_today[0]

        # Get MAL link
        mal_data = await self.getMALAnimeInfo(next_airing['title_romaji'])

        # Get crunchyroll link 
        page_info = await self.getAnilistPageInfo(next_airing['id'])
        cr_link = ''

        for link in page_info['external_links']:
            if link['site'].lower() == 'crunchyroll':
                cr_link = link['url']
                break

        timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        anime_embed = discord.Embed(type='rich', colour=10057145, timestamp=timestamp)
        anime_embed.set_author(name='Airing next:')
        anime_embed.set_thumbnail(url=next_airing['image_url_lge'])
        # Check if english title is different from romaji title
        if next_airing['title_english'] != next_airing['title_romaji']:
            anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})\nKnown as **{0[title_english]}**'.format(next_airing), inline=False)
        else:
            anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})'.format(next_airing), inline=False)
        anime_embed.set_footer(text='Info from Anilist', icon_url='https://anilist.co/img/logo_al.png')
        # Get airing time
        countdown = parse(next_airing['airing']['time']) - datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        # Tidy up if unknown eps
        total_ep = int(next_airing['total_episodes'])
        if total_ep == 0:
            total_ep = '-'
        anime_embed.add_field(name='Episode', value='#**{0[airing][next_episode]}**/**{1}**\nAirs in: **{2}**'.format(next_airing, total_ep, str(countdown).split('.')[0]), inline=False)
        # Add links to embed
        links = '[Anilist](https://anilist.co/anime/{0})'.format(next_airing['id'])
        if len(mal_data) > 0:
            links += ' [MAL](https://myanimelist.net/anime/{0})'.format(mal_data[0]['id'])
        if cr_link != '':
            links += ' [Crunchyroll]({0})'.format(cr_link)
        anime_embed.add_field(name='Links:', value=links)
        anime_embed.add_field(name='DM Notification:', value='Type **@{0} anime notify {1}** to get DM notifications for this anime'.format(self.bot.user.name, next_airing['id']))

        await ctx.send(embed=anime_embed)

    @anime.command()
    async def notify(self, ctx, anime_id : str):
        ''' Gets the bot to DM you the anime from id when it comes out
        '''

        # Check if the anime they asked for is airing
        already_notify = False
        if anime_id in self.all_airing_ids:
            if str(anime_id) in self.notifications:
                if ctx.author.id in self.notifications[str(anime_id)]:
                    already_notify = True
                else:
                    self.notifications[str(anime_id)].append(ctx.author.id)
            else:
                self.notifications[str(anime_id)] = []
                self.notifications[str(anime_id)].append(ctx.author.id)

            if already_notify:
                await ctx.send("{0}, I'm already notifying you when {1} comes out!".format(ctx.author.mention, self.all_airing_ids[anime_id]))
            else:
                await ctx.send("Okay {0}, I'll notify you when {1} comes out!".format(ctx.author.mention, self.all_airing_ids[anime_id]))

            # Save notifications.json
            utils.saveCogConfig(self, 'notifications.json', self.notifications)
            
        else:
            await self.bot.say("{0}, There isn't an anime with that ID airing, Did you copy the ID right?".format(ctx.author.mention))

    @anime.command()
    async def stop(self, ctx, anime_id : str):
        ''' Gets the bot to stop DMing you the anime from id when it comes out
        '''

        # Check if the anime they asked for is airing
        already_notify = True
        if anime_id in self.all_airing_ids:
            if str(anime_id) in self.notifications:
                if ctx.author.id in self.notifications[str(anime_id)]:
                    self.notifications[str(anime_id)].remove(ctx.author.id)
                    if len(self.notifications[str(anime_id)]) == 0:
                        self.notifications.pop(str(anime_id))
                else:
                    already_notify = False
            else:
                already_notify = False           
            
            if already_notify:
                await self.bot.say("Okay {0}, I'll stop notifying you when {1} comes out!".format(ctx.author.mention, self.all_airing_ids[anime_id]))
            else:
                await self.bot.say("{0}, I'll wasn't notifying you when {1} came out!".format(ctx.author.mention, self.all_airing_ids[anime_id]))

            # Save notifications.json
            utils.saveCogConfig(self, 'notifications.json', self.notifications)

        else:
            await self.bot.say("{0}, There isn't an anime with that ID airing, Did you copy the ID right?".format(ctx.author.mention))

    @anime.command()
    async def airing(self, ctx):
        ''' Shows all anime airing today
        '''

        desc = ''
        for anime in self.airing_today:
            # Tidy up if unknown eps
            total_ep = int(anime['total_episodes'])
            if total_ep == 0:
                total_ep = '-'
            if anime['airing']['countdown'] is None:
                desc += '[ID: {0[id]}] {0[title_romaji]} [{0[airing][next_episode]}/{1}] - AIRED\n'.format(anime, total_ep)
            else:
                desc += '[ID: {0[id]}] {0[title_romaji]} [{0[airing][next_episode]}/{1}]\n'.format(anime, total_ep) 

        timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
        em = discord.Embed(type='rich', colour=10057145, description=desc, timestamp=timestamp)
        em.set_author(name='Currently Airing Today:')
        em.set_footer(text='Info from Anilist', icon_url='https://anilist.co/img/logo_al.png')

        await ctx.send(embed=em)

    @anime.command()
    async def info(self, ctx, *, title : str):
        ''' Get anilist info from romaji title
        '''

        anime_found = False
        anime_id = None

        for aniID, aniTitle in self.all_airing_ids.items():
            if aniTitle == title:
                anime_found = True
                anime_id = aniID
                break

        if anime_found:
            anime_info = await self.getAnilistPageInfo(anime_id)

            # Get MAL link
            mal_data = await self.getMALAnimeInfo(anime_info['title_romaji'])

            # Get CrunchyRoll link
            cr_link = ''

            for link in anime_info['external_links']:
                if link['site'].lower() == 'crunchyroll':
                    cr_link = link['url']
                    break

            timestamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            anime_embed = discord.Embed(type='rich', colour=10057145, timestamp=timestamp)
            anime_embed.set_author(name='Anime Info:')
            anime_embed.set_thumbnail(url=anime_info['image_url_lge'])
            # Check if english title is different from romaji title
            if anime_info['title_english'] != anime_info['title_romaji']:
                anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})\nKnown as **{0[title_english]}**'.format(anime_info), inline=False)
            else:
                anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})'.format(anime_info), inline=False)
            anime_embed.set_footer(text='Info from Anilist', icon_url='https://anilist.co/img/logo_al.png')
            # Get airing time
            countdown = parse(anime_info['airing']['time']) - datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
            # Tidy up if unknown eps
            total_ep = int(anime_info['total_episodes'])
            if total_ep == 0:
                total_ep = '-'
            anime_embed.add_field(name='Episode', value='#**{0[airing][next_episode]}**/**{1}**\nAirs in: **{2}**'.format(anime_info, total_ep, str(countdown).split('.')[0]), inline=False)
            # Add links to embed
            links = '[Anilist](https://anilist.co/anime/{0})'.format(anime_info['id'])
            if len(mal_data) > 0:
                links += ' [MAL](https://myanimelist.net/anime/{0})'.format(mal_data[0]['id'])
            if cr_link != '':
                links += ' [Crunchyroll]({0})'.format(cr_link)
            anime_embed.add_field(name='Links:', value=links)
            anime_embed.add_field(name='DM Notification:', value='Type **@{0} anime notify {1}** to get DM notifications for this anime'.format(self.bot.user.name, anime_info['id']))

            await ctx.send(embed=anime_embed)
        else:
            await ctx.send("{0}, I couldn't find that anime. Make sure you are using the romaji title for this command please".format(ctx.author.mention))

def setup(bot):
    n = animestuff(bot)
    bot.add_cog(n)