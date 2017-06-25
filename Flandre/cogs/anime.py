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

    def __hash__(self):
        return self.id ^ hash(self.title) ^ hash(self.next_episode)

    def __str__(self):
        total_ep = int(self.total_episodes)
        if total_ep == 0:
            total_ep = '-'
        return f'[ID: {self.id}] {self.title} [{self.next_episode}/{total_ep}]\n'


    def recalculate_countdown(self, time_now):
        ''' Recalculates the countdown from the current time '''

        countdown = parse(self.release_time) - time_now
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

        self.airing = []
        self.airing_today = []
        self.all_airing_ids = {}
        self.anime_to_be_released = asyncio.Event()

        self.token = None
        self.token_task = self.loop.create_task(self.get_token)

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

            l = []
            for entries in tree:
                for entry in entries:
                    l.append(dict(entry.tag, entry.text))
            return l
        except:
            return []

    async def get_page_info(self, id):
        return await self.page_cache.get(id)

    async def _fetch_page_info(self, id):
        '''
        Fetches the anime page info from Anilist
        using the given Anilist id
        '''

        if self.token is not None:
            # Set up request and params
            request_url = f'https://anilist.co/api/anime/{id}/page'
            params = {'access_token': self.token}

            # Make request
            async with self.session.get(request_url, params=params) as resp:
                data = await resp.json()
            return data

        else:
            return {}

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

                # Remove hentai as it has no airing info for some reason and add to airong list
                for anime in animes:
                    if anime['airing'] is not None:
                        self.airing.append(Show(anime))

                # Put all airing animes in a dict with id as key and title as value
                self.all_airing_ids = {str(k.id): k.title for k in self.airing}

                # Remove any anime that is no longer airing
                removed_counter = 0 # Remove counter for log
                for notify_id in self.cog.notifications.copy():
                    if notify_id not in self.all_airing_ids:
                        self.cog.notifications.pop(notify_id)
                        removed_counter += 1

                # Save notifications.json
                utils.save_cog_config(self, 'notifications.json', self.cog.notifications)
                log_msg = (f'Found {len(animes)} currently airing anime. '
                           f'Removed {removed_counter} no longer airing anime from notification file')
                self.cog.bot.logger.info(log_msg)

                # Get current date and reset airing today
                today = now()
                midnight_tomorrow = today + datetime.timedelta(days=1)
                midnight_tomorrow = midnight_tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                self.airing_today = []

                # Get all anime that airs today
                for anime in animes:
                    airdate = anime.release_time
                    # Check if it airs today
                    if airdate <= midnight_tomorrow:
                        if anime in self.airing_today:
                            continue
                        else:
                            self.airing_today.append(anime)

                # Double Check for dups
                self.airing_today = list(set(self.airing_today))

                # Check if we have any airing
                if self.airing_today:

                    # Sort anime airing today by the countdown suppied by anilist
                    # Will be wrong when working with it but it tells us what should air first,
                    # We will calculate the true time from the time given
                    # If it has aired it will be none but when we get it here it shouldn't be none
                    self.airing_today = sorted(self.airing_today,
                                               key=lambda x: (x.countdown is None,
                                                              x.countdown))

                    # Tell the airing background task that there is anime airing today
                    self.anime_to_be_released.set()

                    # Make an embed to tell users what airs today
                    desc = ''
                    for anime in self.airing_today:
                        desc += str(anime)

                    timestamp = now()
                    embed = discord.Embed(type='rich',
                                          colour=10057145,
                                          description=desc,
                                          timestamp=timestamp)

                    embed.set_author(name='Airing today:')
                    embed.set_footer(text='Info from Anilist', icon_url=ANILIST_ICON)

                    # Send Embed
                    if self.cog.subbed_channels:
                        for channel in self.cog.subbed_channels['channels']:
                            subbed_channel = self.cog.bot.get_channel(channel)
                            await subbed_channel.send(embed=embed)

                # Wait for the next day
                next_day = now() + datetime.timedelta(days=1)
                time_left = next_day.replace(hour=0, minute=2, second=0, microsecond=0) - now()
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


    async def __local_check(self, ctx):
        ''' The cog disabled check '''
        return utils.check_enabled(ctx)

def setup(bot):
    ''' Add cog to bot '''
    cog = Anime(bot)
    bot.add_cog(cog)
