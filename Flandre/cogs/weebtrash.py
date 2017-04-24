import discord
from discord.ext import commands
import asyncio
import aiohttp
import json
import xml.etree.ElementTree as et
from datetime import datetime, timedelta, date
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
        self.notifications = {}
        self.loaded_config = False
        self.loadConfig()
        if self.loaded_config:
            self.token = ""
            self.token_refresher = self.bot.loop.create_task(self.tokenRefresher())
            self.next_airing = None
            self.next_airing_sender = self.bot.loop.create_task(self.nextAiringSender())
            self.hourly_notifyer = self.bot.loop.create_task(self.hourlyNotifyer())
            self.airing_checker = self.bot.loop.create_task(self.airingNotificationChecker())

    async def _unload(self):
        ''' Unload function for when it is unloaded
        '''
        # Cancel all background tasks
        if self.loadConfig:
            self.token_refresher.cancel()
            self.next_airing_sender.cancel()
            self.hourly_notifyer.cancel()
            self.airing_checker.cancel()

    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages

    def loadConfig(self):
        ''' Loads the files for the cogs stored in the cogs data folder
        '''

        if not isdir('Flandre/data/weebtrash'):
            # Make the directory if missing and the files that go with it 
            self.bot.log('warn', 'Cogs data folder not found, it and all files have been made')
            mkdir('Flandre/data/weebtrash')
            with open('Flandre/data/weebtrash/config.json', 'w') as file:
                json.dump({"anilist": {"clientID": "", "clientSecret": ""}, "mal": {"username": "", "password": ""}}, file, indent=4, sort_keys=True)
            with open('Flandre/data/weebtrash/subbed_channels.json', 'w') as file:
                json.dump({'channels': []}, file, indent=4, sort_keys=True)
            with open('Flandre/data/weebtrash/notifications.json', 'w') as file:
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
                    json.dump({"anilist": {"clientID": "", "clientSecret": ""}, "mal": {"username": "", "password": ""}}, file, indent=4, sort_keys=True)
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
                    json.dump({'channels': []}, file, indent=4, sort_keys=True)
                self.bot.log('info', 'Flandre/data/weebtrash/subbed_channels.json has been remade for you')
            # Check for notifications file
            try:
                with open('Flandre/data/weebtrash/notifications.json', 'r') as file:
                    self.notifications = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.notifications = {}
                self.bot.log('error', 'notifications.json could not be loaded. Reason: {0}'.format(e))                
                # Make the file for user again
                with open('Flandre/data/weebtrash/notifications.json', 'w') as file:
                    json.dump({}, file, indent=4, sort_keys=True)
                self.bot.log('info', 'Flandre/data/weebtrash/notifications.json has been remade for you')

    async def tokenRefresher(self):
        ''' Background task to refresh anilist api token every hour
        '''
        
        # Set up POST data to get token
        auth_url = 'https://anilist.co/api/auth/access_token'
        auth_data = {'grant_type': "client_credentials", 'client_id': self.config['anilist']['clientID'], 'client_secret': self.config['anilist']['clientSecret']}
        while True:
            
            # Request token
            with aiohttp.ClientSession() as aioclient:
                async with aioclient.post(auth_url, data=auth_data) as resp:
                    status_code = resp.status
                    data = await resp.json()

            # Save token and wait untill it expires
            self.token = data['access_token']
            await asyncio.sleep(data['expires_in'])

    async def getAiringAnilistAPIData(self):
        ''' Gets AniList API currently airing anime data and sorts it by next release
        '''

        # Set up request and params
        request_url = 'https://anilist.co/api/browse/anime'
        params = {'access_token': self.token, 'year': str(date.today().year),'status': 'Currently Airing', 'airing_data': True}

        # Make request
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(request_url, params=params) as resp:
                status_code = resp.status
                data = await resp.json()

        # Remove any anime that has no airing info due to it being unknown
        for anime in data.copy():
            if anime['airing'] is None:
                data.remove(anime)

        # Sort data so next airing is 1st then the one after and so on
        data = sorted(data, key=lambda k: k['airing'].get('countdown'))
        return data

    async def getAnilistPageInfo(self, id):
        ''' Gets page info for anime from ID (Mainly used to get crunchyroll link)
        '''

        # Set up request and params
        request_url = 'https://anilist.co/api/anime/{0}/page'.format(self.next_airing['id'])
        params = {'access_token': self.token}

        # Make request
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(request_url, params=params) as resp:
                status_code = resp.status
                data = await resp.json()

        return data

    async def getMALAnimeInfo(self, anime):
        ''' Get MAL anime info from name
        '''
        # Remove spaces for web request
        anime = anime.replace(' ', '_')

        try:
            # Request Information
            with aiohttp.ClientSession() as aioclient:
                async with aioclient.get('https://myanimelist.net/api/anime/search.xml?q={0}'.format(anime), auth=aiohttp.BasicAuth(self.config['mal']['username'], self.config['mal']['password'])) as resp:
                    data = await resp.text()
                    data = et.fromstring(data)

            return [i for i in [dict((info.tag, info.text) for info in entrys) for entrys in data]]
        except:
            return []

    async def nextAiringSender(self):
        ''' Gets the next airing episode and posts in subbed channels when it comes out
        '''
        
        # Wait for token
        await asyncio.sleep(1)
        while True:
            # Grab api data and save the next airing anime
            data = await self.getAiringAnilistAPIData()
            self.next_airing = data[0]
            del data

            # Wait until it airs
            await asyncio.sleep(self.next_airing['airing']['countdown'])

            # Get anime page info for crunchyroll link
            page_info = await self.getAnilistPageInfo(self.next_airing['id'])
            cr_link = ''

            for link in page_info['external_links']:
                if link['site'].lower() == 'crunchyroll':
                    cr_link = link['url']
                    break

            # Get MAL link
            mal_data = await self.getMALAnimeInfo(self.next_airing['title_romaji'])

            # Create embed
            em = discord.Embed(type='rich', colour=10057145, description='Episode **{0[airing][next_episode]}** of **{0[title_romaji]} ({0[type]})**'.format(self.next_airing))
            em.set_author(name='Just Released:')
            # Add crunchyroll link to embed if it was found
            if cr_link != '':
                em.description += '\nWatch on [Crunchyroll]({0})'.format(cr_link)
            em.set_thumbnail(url=self.next_airing['image_url_lge'])
            # Add links to embed
            links = '[Anilist](https://anilist.co/anime/{0})'.format(self.next_airing['id'])
            if len(mal_data) > 0:
                links += ' [MAL](https://myanimelist.net/anime/{0})'.format(mal_data[0]['id'])
            em.add_field(name='Links:', value=links)
            em.add_field(name='DM Notification:', value='Type **@{0} anime notify {1}** to get DM notifications for this anime'.format(self.bot.user.name, self.next_airing['id']))
            em.set_footer(text='Info from Anilist | {0}'.format(datetime.now().strftime('%c')), icon_url='https://anilist.co/img/logo_al.png')

            # Send Embed
            if len(self.subbed_channels) > 0:
                for channel in self.subbed_channels['channels']:
                    subbed_channel = self.bot.get_channel(channel)
                    await self.bot.send_message(subbed_channel, embed=em)

            if str(self.next_airing['id']) in self.notifications:
                for user_id in self.notifications[str(self.next_airing['id'])]:
                    try:
                        user = discord.utils.get(self.bot.get_all_members(), id=user_id)
                        if user is not None:
                            await self.bot.send_message(user, embed=em)
                    except:
                        continue

            await asyncio.sleep(1)

    async def hourlyNotifyer(self):
        ''' Checks every hour (on the hour) and post if anything is airing in that hour 
        '''
        
        # Wait for the next exact hour
        next_hour = datetime.now() + timedelta(hours=1)
        time_left = next_hour.replace(minute=0, second=0, microsecond=0) - datetime.now()
        await asyncio.sleep(round(time_left.total_seconds()))

        while True:
            # Get animes all airing anime
            data = await self.getAiringAnilistAPIData()
            airing_soon = []
            
            # Get all anime airing within the hour seconds <= 3660 but more that a min away
            for anime in data:
                if anime['airing']['countdown'] <= 3660 and anime['airing']['countdown'] > 60:
                    airing_soon.append(anime)

            del data

            # Check if there are any airing soon
            if len(airing_soon) > 0:
                # Create description
                desc = ''
                for i, anime in enumerate(airing_soon):
                    m, s = divmod(anime['airing']['countdown'], 60)
                    h, m = divmod(m, 60)
                    # Tidy up if unknown eps
                    total_ep = int(anime['total_episodes'])
                    if total_ep == 0:
                        total_ep = '-'
                    desc += '{0}: [{1[title_romaji]}](https://anilist.co/anime/{1[id]}) ({1[type]}) [{1[airing][next_episode]}/{2}] in {3} Hours {4} Minutes\n'.format((i+1), anime, total_ep ,h, m)
                
                # Create embed
                em = discord.Embed(type='rich', colour=10057145, description=desc)
                em.set_author(name='Airing within the next hour:')
                em.set_footer(text='Info from Anilist | {0}'.format(datetime.now().strftime('%c')), icon_url='https://anilist.co/img/logo_al.png')

                # Send Embed
                if len(self.subbed_channels) > 0:
                    for channel in self.subbed_channels['channels']:
                        subbed_channel = self.bot.get_channel(channel)
                        await self.bot.send_message(subbed_channel, embed=em)

            # Wait for the next exact hour
            next_hour = datetime.now() + timedelta(hours=1)
            time_left = next_hour.replace(minute=0, second=0, microsecond=0) - datetime.now()
            await asyncio.sleep(round(time_left.total_seconds()))

    async def airingNotificationChecker(self):
        ''' Checks if animes in DM notifications is still airing
            if not it is removed from the file. Checks daily
        '''
        # Wait for the next day
        next_day = datetime.now() + timedelta(days=1)
        time_left = next_day.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.now()
        await asyncio.sleep(round(time_left.total_seconds()))

        while True:
            counter = 0
            # Get animes all airing anime ids
            airing_ids = [str(d['id']) for d in await self.getAiringAnilistAPIData()]

            for notif_id in self.notifications.copy():
                if notif_id not in airing_ids:
                    self.notifications.pop(str(notif_id))
                    counter +=1

            self.bot.log('info', 'Daily anime notification checker ran. Removed: {0}'.format(counter))
            
            # Save notifications.json
            try:
                with open('Flandre/data/weebtrash/notifications.json', 'w') as file:
                    json.dump(self.notifications, file, indent=4, sort_keys=True)
            except:
                self.bot.log('critical', 'Flandre/data/weebtrash/notifications.json could not be saved. Please check it')
            else:
                self.bot.log('info', 'Flandre/data/weebtrash/notifications.json has been saved.')

            # Wait for the next day
            next_day = datetime.now() + timedelta(days=1)
            time_left = next_day.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.now()
            await asyncio.sleep(round(time_left.total_seconds()))


    @commands.group(pass_context=True)
    async def anime(self, ctx) :
        ''' Anime commands 
            Uses AniList and MAL
        '''
        
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
            

    @anime.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def sub(self, ctx):
        ''' Tells bot to use this channel when an anime comes out
            Using it again will remove the channel
        '''

        removed = False
        if ctx.message.channel.id in self.subbed_channels['channels']:
            self.subbed_channels['channels'].remove(ctx.message.channel.id)
            removed = True
        else:
            self.subbed_channels['channels'].append(ctx.message.channel.id)
        
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

    @anime.command(name='next', pass_context=True)
    async def anime_next(self, ctx):
        ''' Displays info on the next airing anime
        '''

        # Get updated airing time
        air_times = [d['airing']['countdown'] for d in await self.getAiringAnilistAPIData()]

        # Get MAL link
        mal_data = await self.getMALAnimeInfo(self.next_airing['title_romaji'])

        # Get crunchyroll link 
        page_info = await self.getAnilistPageInfo(self.next_airing['id'])
        cr_link = ''

        for link in page_info['external_links']:
            if link['site'].lower() == 'crunchyroll':
                cr_link = link['url']
                break

        anime_embed = discord.Embed(type='rich', colour=10057145)
        anime_embed.set_author(name='Airing next:')
        anime_embed.set_thumbnail(url=self.next_airing['image_url_lge'])
        # Check if english title is different from romaji title
        if self.next_airing['title_english'] != self.next_airing['title_romaji']:
            anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})\nKnown as **{0[title_english]}**'.format(self.next_airing), inline=False)
        else:
            anime_embed.add_field(name='Title', value='{0[title_romaji]} ({0[type]})'.format(self.next_airing), inline=False)
        anime_embed.set_footer(text='Info from Anilist | {0}'.format(datetime.now().strftime('%c')), icon_url='https://anilist.co/img/logo_al.png')
        # Get airing time in h,m,s
        m, s = divmod(air_times[0], 60)
        h, m = divmod(m, 60)
        # Tidy up if unknown eps
        total_ep = int(self.next_airing['total_episodes'])
        if total_ep == 0:
            total_ep = '-'
        anime_embed.add_field(name='Episode', value='#**{0[airing][next_episode]}**/**{1}**\nAirs in: **{2} hours {3} mins**'.format(self.next_airing, total_ep, h, m), inline=False)
        # Add links to embed
        links = '[Anilist](https://anilist.co/anime/{0})'.format(self.next_airing['id'])
        if len(mal_data) > 0:
            links += ' [MAL](https://myanimelist.net/anime/{0})'.format(mal_data[0]['id'])
        if cr_link != '':
            links += ' [Crunchyroll]({0})'.format(cr_link)
        anime_embed.add_field(name='Links:', value=links)
        anime_embed.add_field(name='DM Notification:', value='Type **@{0} anime notify {1}** to get DM notifications for this anime'.format(self.bot.user.name, self.next_airing['id']))

        await self.bot.send_message(ctx.message.channel, embed=anime_embed)

    @anime.command(pass_context=True)
    async def notify(self, ctx, anime_id : str):
        ''' Gets the bot to DM you the anime from id when it comes out
        '''

        # Get all airing anime ID's and names in a dict
        airing_ids =  {str(k['id']): k['title_romaji'] for k in await self.getAiringAnilistAPIData()}

        # Check if the anime they asked for is airing
        already_notify = False
        if anime_id in airing_ids:
            if str(anime_id) in self.notifications:
                if ctx.message.author.id in self.notifications[str(anime_id)]:
                    already_notify = True
                else:
                    self.notifications[str(anime_id)].append(ctx.message.author.id)
            else:
                self.notifications[str(anime_id)] = []
                self.notifications[str(anime_id)].append(ctx.message.author.id)

            if already_notify:
                await self.bot.say("{0}, I'm already notifying you when {1} comes out!".format(ctx.message.author.mention, airing_ids[anime_id]))
            else:
                await self.bot.say("Okay {0}, I'll notify you when {1} comes out!".format(ctx.message.author.mention, airing_ids[anime_id]))

            # Save notifications.json
            try:
                with open('Flandre/data/weebtrash/notifications.json', 'w') as file:
                    json.dump(self.notifications, file, indent=4, sort_keys=True)
            except Exception as e:
                self.bot.log('critical', 'Flandre/data/weebtrash/notifications.json could not be saved. Please check it Reason: {0}'.format(e))
            else:
                self.bot.log('info', 'Flandre/data/weebtrash/notifications.json has been saved.')
        else:
            await self.bot.say("{0}, There isn't an anime with that ID airing, Did you copy the ID right?".format(ctx.message.author.mention))

    @anime.command(pass_context=True)
    async def stop(self, ctx, anime_id : str):
        ''' Gets the bot to stop DMing you the anime from id when it comes out
        '''

        # Get all airing anime ID's and names in a dict
        airing_ids =  {str(k['id']): k['title_romaji'] for k in await self.getAiringAnilistAPIData()}

        # Check if the anime they asked for is airing
        already_notify = True
        if anime_id in airing_ids:
            if str(anime_id) in self.notifications:
                if ctx.message.author.id in self.notifications[str(anime_id)]:
                    self.notifications[str(anime_id)].remove(ctx.message.author.id)
                    if len(self.notifications[str(anime_id)]) == 0:
                        self.notifications.pop(str(anime_id))
                else:
                    already_notify = False
            else:
                already_notify = False           
            
            if already_notify:
                await self.bot.say("Okay {0}, I'll stop notifying you when {1} comes out!".format(ctx.message.author.mention, airing_ids[anime_id]))
            else:
                await self.bot.say("{0}, I'll wasn't notifying you when {1} came out!".format(ctx.message.author.mention, airing_ids[anime_id]))

            # Save notifications.json
            try:
                with open('Flandre/data/weebtrash/notifications.json', 'w') as file:
                    json.dump(self.notifications, file, indent=4, sort_keys=True)
            except Exception as e:
                self.bot.log('critical', 'Flandre/data/weebtrash/notifications.json could not be saved. Please check it Reason: {0}'.format(e))
            else:
                self.bot.log('info', 'Flandre/data/weebtrash/notifications.json has been saved.')
        else:
            await self.bot.say("{0}, There isn't an anime with that ID airing, Did you copy the ID right?".format(ctx.message.author.mention))

    @anime.command(pass_context=True)
    async def airing(self, ctx):
        ''' Shows all airing anime with a known release
        '''

        data = await self.getAiringAnilistAPIData()

        desc = ''
        for anime in data:
            # Tidy up if unknown eps
            total_ep = int(self.next_airing['total_episodes'])
            if total_ep == 0:
                total_ep = '-'
            desc += '[ID: {0[id]}] {0[title_romaji]} [{0[airing][next_episode]}/{1}]\n'.format(anime, total_ep) 

        em = discord.Embed(type='rich', colour=10057145, description=desc)
        em.set_author(name='Currently Airing:')
        em.set_footer(text='Info from Anilist | {0}'.format(datetime.now().strftime('%c')), icon_url='https://anilist.co/img/logo_al.png')

        await self.bot.send_message(ctx.message.channel, embed=em)

def setup(bot):
    n = weebtrash(bot)
    bot.add_cog(n)