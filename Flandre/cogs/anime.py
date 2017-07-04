''' Holds all anime commands and functions for the bot '''
import asyncio
import datetime
import xml.etree.ElementTree as et
import re

import aiohttp
import discord
from discord.ext import commands
from dateutil.parser import parse

from .. import permissions, utils

DEFAULT = {"anilist": {"clientID": "", "clientSecret": ""},
           "mal": {"username": "", "password": ""},
          }
ANILIST_ICON = 'https://anilist.co/img/logo_al.png'
MAL_ICON = 'https://myanimelist.cdn-dena.com/images/faviconv5.ico'

BREAK_REGEX = re.compile(r'<br(?: /)?>', re.IGNORECASE)
BOLD_REGEX = re.compile(r'\[b/?\]')
ITALICS_REGEX = re.compile(r'\[i/?\]')
UNDERLINE_REGEX = re.compile(r'\[u/?\]')
STRIKETHROUGH_REGEX = re.compile(r'\[s/?\]')

def clean_synopsis(synopsis):
    '''
    Cleans a synopsis to replace certain characters
    And format for markdown
    '''

    # Remove <br /> so it prints just a new line
    synopsis = BREAK_REGEX.sub('', synopsis)

    # Convert html formating with correct characters
    synopsis = synopsis.replace('&mdash;', '—')
    synopsis = synopsis.replace('&ndash;', '-')
    synopsis = synopsis.replace('&sect;', '§')
    synopsis = synopsis.replace('&ldquo;', '"')
    synopsis = synopsis.replace('&rdquo;', '"')
    synopsis = synopsis.replace('&quot;', '"')
    synopsis = synopsis.replace('&#039;', "'")

    # Replace style with markdown
    synopsis = BOLD_REGEX.sub('**', synopsis)
    synopsis = ITALICS_REGEX.sub('_', synopsis)
    synopsis = UNDERLINE_REGEX.sub('__', synopsis)
    synopsis = STRIKETHROUGH_REGEX.sub('~~', synopsis)

    return synopsis

def now():
    ''' Gets the current time in the Japanese timezone (GMT+9)
    '''

    tz = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(tz)

class Show:
    '''
    This holds all the infomation we need about a anime
    from anilist for the anime cog
    '''

    def __init__(self, anime):
        self.id = anime.get('id')
        self.title = anime.get('title_romaji')
        self.english_title = anime.get('title_english')
        self.type = anime.get('type')
        self.total_episodes = anime.get('total_episodes')
        self.image_url = anime.get('image_url_lge')
        self.next_episode = anime['airing'].get('next_episode')
        self.countdown = anime['airing'].get('countdown')
        self.release_time = parse(anime['airing'].get('time'))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.id == other.id and self.title == other.title and self.next_episode == other.next_episode

    def __hash__(self):
        return hash(self.id) ^ hash(self.title) ^ hash(self.next_episode)

    def __repr__(self):
        return f'<Anime - ID: {self.id}, Title: {self.title}, Next: {self.next_episode}>'

    def __str__(self):
        total_ep = int(self.total_episodes)
        if total_ep == 0:
            total_ep = '-'
        return f'[ID: {self.id}] {self.title} [{self.next_episode}/{total_ep}]'


    def recalculate_countdown(self, time_now):
        ''' Recalculates the countdown from the current time '''

        countdown = self.release_time - time_now
        self.countdown = round(countdown.total_seconds())

class LruCache:
    def __init__(self, retriever, capacity=128):
        self.cache = {}
        self.retriever = retriever
        self.atime = 0
        self.capacity = capacity

    async def get(self, id):
        '''
        Get the object with the given ID from the cache,
        if it exists, otherwise it calls the retrieval
        function to fetch it.
        '''

        self.atime += 1
        try:
            entry = self.cache[id]
            entry[1] = self.atime
            return entry[0]
        except KeyError:
            if len(self.cache) >= self.capacity:
                self._evict()
            item = await self.retriever(id)
            self.cache[id] = [item, self.atime]
            return item

    def remove(self, id):
        if id not in self.cache:
            return
        
        del self.cache[id]
    
    def _evict(self):
        '''
        Removes the least recently used item
        from the cache. This method asumes
        a non-empty cache.
        '''

        min_id = None
        min_time = -1
        for id, [item, atime] in self.cache.items():
            if min_id is None or min_time > atime:
                min_id = id
                min_time = atime
        del self.cache[min_id]

class AnimePool:

    def __init__(self, cog):
        self.cog = cog
        self.loop = cog.bot.loop
        self.session = aiohttp.ClientSession()

        self.mal_cache = LruCache(self._fetch_mal_info)
        self.page_cache = LruCache(self._fetch_page_info)

        self.airing_today = []
        self.all_airing_ids = {}
        self.anime_to_be_released = asyncio.Event()

        self.token = None
        self.token_task = self.loop.create_task(self.get_token())
        self.daily_anime_grabber = self.loop.create_task(self.daily_anime_task())
        self.next_airing_sender = self.loop.create_task(self.next_airing_task())
        self.hourly_notify = self.loop.create_task(self.hourly_notifyer_task())

    async def get_mal_info(self, title):
        return await self.mal_cache.get(title)

    async def _fetch_mal_info(self, title):
        '''
        Fetches an anime from the MAL API
        using the given title.
        '''

        # Remove spaces for web request
        anime = title.replace(' ', '_')
        url = f'https://myanimelist.net/api/anime/search.xml?q={anime}'
        config = self.cog.config
        auth = aiohttp.BasicAuth(config['mal']['username'], config['mal']['password'])

        try:
            # Request information
            async with self.session.get(url, auth=auth) as resp:
                data = await resp.text()
                tree = et.fromstring(data)

            return [i for i in [dict((info.tag, info.text) for info in entrys) for entrys in tree]]
        except:
            return []

    async def get_page_info(self, aid):
        return await self.page_cache.get(aid)

    async def _fetch_page_info(self, aid):
        '''
        Fetches the anime page info from Anilist
        using the given Anilist id
        '''

        if self.token is not None:
            # Set up request and params
            request_url = f'https://anilist.co/api/anime/{aid}/page'
            params = {'access_token': self.token}

            # Make request
            async with self.session.get(request_url, params=params) as resp:
                data = await resp.json()
            return data

        else:
            return {}
    
    def make_airing_embed(self):
        '''
        Makes a embed with everything that is airing
        '''

        desc = ''
        for anime in self.airing_today:
            if anime.countdown is None:
                desc += f'{str(anime)} - AIRED\n'

            else:
                desc += f'{str(anime)}\n'

        timestamp = now()
        embed = discord.Embed(type='rich',
                                colour=10057145,
                                description=desc,
                                timestamp=timestamp)

        embed.set_author(name='Airing today:')
        embed.set_footer(text='Info from Anilist', icon_url=ANILIST_ICON)
        
        return embed

    async def get_token(self):
        ''' Background task to refresh anilist api token every hour '''

        # Set up POST data to get token
        auth_url = 'https://anilist.co/api/auth/access_token'
        auth_data = {'grant_type': "client_credentials",
                     'client_id': self.cog.config['anilist']['clientID'],
                     'client_secret': self.cog.config['anilist']['clientSecret'],
                    }

        while True:
            # Request token
            async with self.session.post(auth_url, data=auth_data) as resp:
                status_code = resp.status
                data = await resp.json()

            # Check if request was successful
            if status_code == 200:
                # Save token and wait until it expires
                self.token = data['access_token']
                await asyncio.sleep(data['expires_in'])

            else:
                self.token = None
                break

    async def daily_anime_task(self):
        ''' Function that does all daily checks and get all anime airing that day '''

        # Wait for token before we do anything
        await asyncio.sleep(2)

        if self.token is not None:
            while True:
                # Set up request to get all airing anime
                request_url = 'https://anilist.co/api/browse/anime'
                page = 0 # Page number for api request
                page_number_found = 40 # Number of anime found (if < 40 found we have them all)
                # Current year
                year = str(now().year)
                animes = []

                while page_number_found == 40:
                    # Make params
                    params = {'access_token': self.token,
                              'year': year,
                              'status': 'Currently Airing',
                              'airing_data': 'True',
                              'page': page,
                             }

                    # Make request
                    async with self.session.get(request_url, params=params) as resp:
                        data = await resp.json()

                    # Add anime found to list, increase page number, and set page_number_found
                    animes += data
                    page += 1
                    page_number_found = len(data)

                
                # Get current date and reset airing today
                today = now()
                midnight_tomorrow = today + datetime.timedelta(days=1)
                midnight_tomorrow = midnight_tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                self.airing_today = []
                
                # Remove hentai as it has no airing info
                # Then add the title mapped to the id for nofitications
                # Then check if it is airing today
                for anime in animes:
                    if anime['airing'] is not None:
                        self.all_airing_ids[str(anime['id'])] = anime['title_romaji']
                        
                        # Check if it airs today
                        airdate = parse(anime['airing']['time'])
                        if airdate <= midnight_tomorrow:
                            self.airing_today.append(Show(anime))

                # Remove any anime that is no longer airing from notifications file
                removed_counter = 0 # Remove counter for log
                for notify_id in self.cog.notifications.copy():
                    if notify_id not in self.all_airing_ids:
                        self.cog.notifications.pop(notify_id)
                        removed_counter += 1

                # Save notifications.json
                log_msg = (f'Found {len(self.all_airing_ids)} currently airing anime. '
                           f'Removed {removed_counter} no longer airing anime from notification file')
                self.cog.bot.logger.info(log_msg)
                utils.save_cog_config(self.cog, 'notifications.json', self.cog.notifications)

                # Check for dups and remove them
                self.airing_today = list(set(self.airing_today))

                # Check if we have any airing
                if self.airing_today:

                    # Sort anime airing today by the countdown suppied by anilist
                    # Will be wrong when working with it but it tells us what should air first,
                    # We will calculate the true time from the time given later
                    # If it has aired it will be none but when we get it here it shouldn't be none
                    self.airing_today = sorted(self.airing_today,
                                               key=lambda x: (x.countdown is None,
                                                              x.countdown))

                    # Tell the airing background task that there is anime airing today
                    self.anime_to_be_released.set()

                    # Make an embed to tell users what airs today
                    embed = self.make_airing_embed()

                    # Send Embed
                    if self.cog.subbed_channels:
                        for channel in self.cog.subbed_channels['channels']:
                            subbed_channel = self.cog.bot.get_channel(channel)
                            await subbed_channel.send(embed=embed)

                # Wait for the next day
                next_day = now() + datetime.timedelta(days=1)
                time_left = next_day.replace(hour=0, minute=2, second=0, microsecond=0) - now()
                await asyncio.sleep(round(time_left.total_seconds()))

    async def next_airing_task(self):
        ''' Gets the next airing episode and posts in subbed channels when it comes out '''
        # Wait for token
        await asyncio.sleep(1)
        
        if self.token is not None:
            while True:
                await self.anime_to_be_released.wait()
                self.anime_to_be_released.clear()

                # Recalculate countdown
                time_now = now()
                for i, anime in enumerate(self.airing_today.copy()):
                    if anime.countdown != None:
                        anime.recalculate_countdown(time_now)

                self.airing_today = sorted(self.airing_today,
                                           key=lambda x: (x.countdown is None, x.countdown))

                # Get first anime in list
                anime = self.airing_today[0]

                # If first element countdown is none all has aired
                if anime.countdown != None:
                    await asyncio.sleep(anime.countdown)

                    # Get anime page info for crunchyroll link
                    page_info = await self.get_page_info(anime.id)
                    cr_link = ''

                    for link in page_info['external_links']:
                        if link['site'].lower() == 'crunchyroll':
                            cr_link = link['url']
                            break

                    # Get MAL link
                    mal_data = await self.get_mal_info(anime.title)

                    # Create embed
                    desc = (f'Episode **{anime.next_episode}** of '
                            f'**{anime.title} ({anime.type})**')

                    timestamp = now()
                    embed = discord.Embed(type='rich',
                                          colour=10057145,
                                          description=desc,
                                          timestamp=timestamp)

                    embed.set_author(name='Just Released:')

                    # Add crunchyroll link to embed if it was found
                    if cr_link:
                        embed.description += f'\nWatch on [Crunchyroll]({cr_link})'
                    embed.set_thumbnail(url=anime.image_url)

                    # Add links to embed
                    links = f'[Anilist](https://anilist.co/anime/{anime.id})'
                    if mal_data:
                        mid = mal_data[0]['id']
                        links += f' [MAL](https://myanimelist.net/anime/{mid})'
                    embed.add_field(name='Links:', value=links)

                    dm_msg = (f'Type **@{self.cog.bot.user.name} anime notify '
                              f'{anime.id}** to get DM notifications for this anime')

                    embed.add_field(name='DM Notification:', value=dm_msg)
                    embed.set_footer(text='Info from Anilist', icon_url=ANILIST_ICON)

                    # Send Embed
                    if self.cog.subbed_channels:
                        for channel in self.cog.subbed_channels['channels']:
                            subbed_channel = self.cog.bot.get_channel(channel)
                            await subbed_channel.send(embed=embed)

                    if str(anime.id) in self.cog.notifications:
                        for user_id in self.cog.notifications[str(anime.id)]:
                            try:
                                user = self.cog.bot.get_user(user_id)
                                if user is not None:
                                    await user.send(embed=embed)
                            except:
                                continue

                    # Set the anime in list countdown to None
                    self.airing_today[0].countdown = None

                    # Remove the anime page from the cache as if it is not removed
                    # It will show a negative release time as it has passed
                    self.page_cache.remove(anime.id)

                all_aired = True
                for anime in self.airing_today:
                    if anime.countdown != None:
                        all_aired = False
                        break

                if all_aired is False:
                    self.anime_to_be_released.set()
    
    async def hourly_notifyer_task(self):
        ''' Checks every hour (on the hour) and post if anything is airing in that hour '''

        # Wait for the next exact hour
        next_hour = now() + datetime.timedelta(hours=1)
        time_left = next_hour.replace(minute=0, second=0, microsecond=0) - now()

        await asyncio.sleep(round(time_left.total_seconds()))

        if self.token is not None:
            while True:
                airing_soon = []
                time_now = now()
                # Get all anime airing within the hour seconds <= 3660 but more that a min away
                for anime in self.airing_today:
                    if anime.countdown != None:
                        countdown = anime.release_time - time_now
                        if (round(countdown.total_seconds()) <= 3660 and
                                round(countdown.total_seconds()) > 60):
                            airing_soon.append(anime)

                # Check if there are any airing soon
                if airing_soon:
                    # Create description
                    desc = ''
                    for i, anime in enumerate(airing_soon):
                        countdown = anime.release_time - now()
                        countdown = str(countdown).split('.')[0]

                        # Tidy up if unknown eps
                        total_ep = int(anime.total_episodes)
                        if total_ep == 0:
                            total_ep = '-'
                        desc += (
                            f'{i+1}: [{anime.title}](https://anilist.co/anime/{anime.id})'
                            f'({anime.type}) [{anime.next_episode}/{total_ep}] '
                            f'in {countdown}\n'
                            )

                    # Create embed
                    timestamp = now()
                    embed = discord.Embed(type='rich',
                                        colour=10057145,
                                        description=desc,
                                        timestamp=timestamp)

                    embed.set_author(name='Airing within the next hour:')
                    embed.set_footer(text='Info from Anilist', icon_url=ANILIST_ICON)

                    # Send Embed
                    if self.cog.subbed_channels:
                        for channel in self.cog.subbed_channels['channels']:
                            subbed_channel = self.cog.bot.get_channel(channel)
                            await subbed_channel.send(embed=embed)

                # Wait for the next exact hour
                next_hour = now() + datetime.timedelta(hours=1)
                time_left = next_hour.replace(minute=0, second=0, microsecond=0) - now()

                await asyncio.sleep(round(time_left.total_seconds()))

class Anime:
    '''
    Cog that has all anime and manga related items.
    Uses the anilist api to get info about that anime/manga
    Works using time in Japan (GMT+9)
    '''

    def __init__(self, bot):
        self.bot = bot
        self.config = utils.check_cog_config(self, 'config.json', default=DEFAULT)
        self.subbed_channels = utils.check_cog_config(self, 'subbed_channels.json', default={'channels': []})
        self.notifications = utils.check_cog_config(self, 'notifications.json')
        self.anime_pool = AnimePool(self)
        self.mal_manga_cache = LruCache(self._fetch_mal_manga)


    def __unload(self):
        ''' Unload function for when it is unloaded
        '''
        # Cancel all background tasks
        self.anime_pool.session.close()
        self.anime_pool.token_task.cancel()
        self.anime_pool.daily_anime_grabber.cancel()
        self.anime_pool.next_airing_sender.cancel()
        self.anime_pool.hourly_notify.cancel()
        self.bot.remove_listener(self.anime_reference, 'on_message')

    async def __local_check(self, ctx):
        ''' The cog disabled check '''
        return utils.check_enabled(ctx)
    
    async def get_mal_manga(self, title):
        return await self.mal_manga_cache.get(title)
    
    async def _fetch_mal_manga(self, title):
        '''
        Fetches an manga from the MAL API
        using the given title.
        '''

        # Remove spaces for web request
        manga = title.replace(' ', '_')
        url = f'https://myanimelist.net/api/manga/search.xml?q={manga}'
        auth = aiohttp.BasicAuth(self.config['mal']['username'], self.config['mal']['password'])

        try:
            # Request information
            async with self.anime_pool.session.get(url, auth=auth) as resp:
                data = await resp.text()
                tree = et.fromstring(data)

            return [i for i in [dict((info.tag, info.text) for info in entrys) for entrys in tree]]
        except:
            return []
    
    def make_mal_anime_embed(self, anime):
        '''
        Make a embed from the mal anime info given
        '''

        # Clean the synopsis then create the embed
        desc = clean_synopsis(anime['synopsis'])
        # Check if desc has more than one paragraph if so tell user to click title for more
        if '\n' in desc:
            desc = desc.split("\n")[0] + ' **... (Click title for more)**'

        title = f'{anime["title"]} ({anime["type"]})'
        url = f'https://myanimelist.net/anime/{anime["id"]}'

        embed = discord.Embed(type='rich',
                              colour=10057145,
                              description=desc,
                              title=title,
                              url=url)

        embed.add_field(name='Status', value=anime['status'])
        embed.add_field(name='Episodes', value=anime['episodes'])
        embed.add_field(name='Start Date', value=anime['start_date'])
        embed.add_field(name='End Date', value=anime['end_date'])

        # Set embed image and MAL image
        embed.set_thumbnail(url=anime['image'])
        embed.set_footer(text='Info from MAL', icon_url=MAL_ICON)

        return embed
    
    def make_mal_manga_embed(self, manga):
        '''
        Make a embed from the mal manga info given
        '''

        # Clean the synopsis then create the embed
        desc = clean_synopsis(manga['synopsis'])
        # Check if desc has more than one paragraph if so tell user to click title for more
        if '\n' in desc:
            desc = desc.split("\n")[0] + ' **... (Click title for more)**'

        title = f'{manga["title"]} ({manga["type"]})'
        url = f'https://myanimelist.net/manga/{manga["id"]}'

        embed = discord.Embed(type='rich',
                              colour=10057145,
                              description=desc,
                              title=title,
                              url=url)

        embed.add_field(name='Status', value=manga['status'])
        embed.add_field(name='Volumes/Chapters', value=f'{manga["volumes"]}/{manga["chapters"]}')
        embed.add_field(name='Start Date', value=manga['start_date'])
        embed.add_field(name='End Date', value=manga['end_date'])

        # Set embed image and MAL image
        embed.set_thumbnail(url=manga['image'])
        embed.set_footer(text='Info from MAL', icon_url=MAL_ICON)

        return embed
    
    @commands.group()
    async def anime(self, ctx):
        '''
        Anime commands
        Uses AniList and MAL
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)
    
    @anime.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def sub(self, ctx):
        '''
        Tells bot to use this channel when an anime comes out
        Using it again will remove the channel
        '''

        removed = False
        if ctx.channel.id in self.subbed_channels['channels']:
            self.subbed_channels['channels'].remove(ctx.channel.id)
            removed = True
        else:
            self.subbed_channels['channels'].append(ctx.channel.id)

        # Save json file
        utils.save_cog_config(self, 'subbed_channels.json', self.subbed_channels)


        if removed:
            await ctx.send('New releases will no longer be sent to this channel.')
            self.bot.logger.info((f'{ctx.channel.name} ({ctx.channel.id}) '
                                  'has been removed as a subbed channel'))

        else:
            await ctx.send('New releases will be sent to this channel.')
            self.bot.logger.info((f'{ctx.channel.name} ({ctx.channel.id}) '
                                  'has been made a subbed channel'))

    @anime.command()
    async def notify(self, ctx, anime_id: str):
        ''' Gets the bot to DM you the anime from id when it comes out '''

        # Check if the anime they asked for is airing
        already_notify = False
        if anime_id in self.anime_pool.all_airing_ids:
            if str(anime_id) in self.notifications:
                if ctx.author.id in self.notifications[str(anime_id)]:
                    self.notifications[str(anime_id)].remove(ctx.author.id)
                    if not self.notifications[str(anime_id)]:
                        self.notifications.pop(str(anime_id))
                    
                    already_notify = True
                else:
                    self.notifications[str(anime_id)].append(ctx.author.id)
            else:
                self.notifications[str(anime_id)] = []
                self.notifications[str(anime_id)].append(ctx.author.id)

            anime = self.anime_pool.all_airing_ids[anime_id]
            if already_notify:
                await ctx.send((f"Okay {ctx.author.mention}, "
                                f"I'll stop notifying you when **{anime}** comes out!"))

            else:
                await ctx.send((f"Okay {ctx.author.mention}, "
                                f"I'll notify you when **{anime}** comes out!"))

            # Save notifications.json
            utils.save_cog_config(self, 'notifications.json', self.notifications)

        else:
            await ctx.send((f"{ctx.author.mention}, "
                            "There isn't an anime with that ID airing, Did you copy the ID right?"))

    @anime.command()
    async def airing(self, ctx):
        ''' Shows all anime airing today '''

        embed = self.anime_pool.make_airing_embed()
        await ctx.send(embed=embed)
    
    @anime.command()
    async def airinfo(self, ctx, *, title: str=None):
        ''' Get anilist info from romaji title will show the next airing if none given '''

        anime_id = None
        if title is None:
            if self.anime_pool.airing_today[0].countdown is not None:
                anime_id = self.anime_pool.airing_today[0].id
        else:
            for aniid, anititle in self.anime_pool.all_airing_ids.items():
                if anititle.lower() == title.lower():
                    anime_id = aniid
                    break

        if anime_id is not None:
            anime_info = await self.anime_pool.get_page_info(anime_id)

            # Get MAL link
            mal_data = await self.anime_pool.get_mal_info(anime_info['title_romaji'])

            # Get CrunchyRoll link
            cr_link = ''

            for link in anime_info['external_links']:
                if link['site'].lower() == 'crunchyroll':
                    cr_link = link['url']
                    break

            timestamp = now()
            anime_embed = discord.Embed(type='rich', colour=10057145, timestamp=timestamp)
            anime_embed.set_author(name='Anime Info:')
            anime_embed.set_thumbnail(url=anime_info['image_url_lge'])

            # Check if english title is different from romaji title
            if anime_info['title_english'] != anime_info['title_romaji']:
                title = (f'{anime_info["title_romaji"]} ({anime_info["type"]})\n'
                         f'Known as **{anime_info["title_english"]}**')

                anime_embed.add_field(name='Title', value=title, inline=False)

            else:
                title = f'{anime_info["title_romaji"]} ({anime_info["type"]})'
                anime_embed.add_field(name='Title', value=title, inline=False)

            anime_embed.set_footer(text='Info from Anilist', icon_url=ANILIST_ICON)
            # Get airing time
            countdown = parse(anime_info['airing']['time']) - now()
            countdown = str(countdown).split('.')[0]

            # Tidy up if unknown eps
            total_ep = int(anime_info['total_episodes'])
            if total_ep == 0:
                total_ep = '-'

            ep_info = (f'#**{anime_info["airing"]["next_episode"]}**/**{total_ep}**\n'
                       f'Airs in: **{countdown}**')

            anime_embed.add_field(name='Episode', value=ep_info, inline=False)

            # Add links to embed
            aid = anime_info['id']
            links = f'[Anilist](https://anilist.co/anime/{aid})'
            if mal_data:
                mid = mal_data[0]['id']
                links += f' [MAL](https://myanimelist.net/anime/{0})'
            if cr_link:
                links += f' [Crunchyroll]({cr_link})'
            anime_embed.add_field(name='Links:', value=links)

            dm_msg = (f'Type **@{self.bot.user.name} anime notify {anime_info["id"]}** '
                      'to get DM notifications for this anime')

            anime_embed.add_field(name='DM Notification:', value=dm_msg)
            await ctx.send(embed=anime_embed)
        else:
            if title is None:
                await ctx.send(f'{ctx.author.mention}, Every thing has finished airing today')
            else:
                await ctx.send((f"{ctx.author.mention}, "
                                "I couldn't find that anime in the list of airing anime. "
                                "Make sure you are using the romaji title for this command please"))
    
    @anime.command()
    async def search(self, ctx, *, anime: str):
        ''' Get info about an anime from MAL '''

        mal_info = await self.anime_pool.get_mal_info(anime)

        if mal_info:
            anime = mal_info[0]

            embed = self.make_mal_anime_embed(anime)

            await ctx.send(embed=embed)

        else:
            await ctx.send("I couldn't find anything from MAL with that search")
    
    @commands.command()
    async def manga(self, ctx, *, manga: str):
        ''' Get info about a manga from MAL '''

        mal_info = await self.get_mal_manga(manga)

        if mal_info:
            manga = mal_info[0]

            embed = self.make_mal_manga_embed(manga)

            await ctx.send(embed=embed)

        else:
            await ctx.send("I couldn't find anything from MAL with that search")
    
    async def anime_reference(self, message):
        '''
        Looks for anime wrapped in {} in a message and posts MAL info about it
        '''

        if message.channel.id in self.subbed_channels['channels']:
            # Find anime refs
            anime_found = re.findall('\{([\w :-]+)\}', message.content, re.IGNORECASE)
            # Find manga refs
            manga_found = re.findall('\[([\w :-]+)\]', message.content, re.IGNORECASE)

            # If anime is found
            if anime_found:
                animes = []
                # Get the MAL info for each anime
                for anime in anime_found:
                    mal_info = await self.anime_pool.get_mal_info(anime)
                    if mal_info:
                        animes.append(mal_info[0])

                if animes:
                    for anime in animes:
                        embed = self.make_mal_anime_embed(anime)
                        await message.channel.send(embed=embed)
            
            # If manga is found
            if manga_found:
                mangas = []
                # Get the MAL info for each manga
                for manga in manga_found:
                    mal_info = await self.get_mal_manga(manga)
                    if mal_info:
                        mangas.append(mal_info[0])

                if mangas:
                    for manga in mangas:
                        embed = self.make_mal_manga_embed(manga)
                        await message.channel.send(embed=embed)

def setup(bot):
    ''' Add cog to bot '''
    cog = Anime(bot)
    bot.add_listener(cog.anime_reference, "on_message")
    bot.add_cog(cog)
