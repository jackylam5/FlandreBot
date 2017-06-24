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
        self._mal_link = None
        self._crunchyroll_link = None

    def recalculate_countdown(self, time_now):
        ''' Recalculates the countdown from the current time '''

        countdown = parse(self.release_time) - time_now
        self.countdown = round(countdown.total_seconds())

class AnimePool:

    def __init__(self):
        self.airing = []
        self.airing_today = []

class Anime:
    '''
    Cog that has all anime and manga related items.
    Uses the anilist api to get info about that anime/manga
    Works using time in Japan (GMT+9)
    '''

    def __init__(self, bot):
        self.bot = bot

    async def __local_check(self, ctx):
        ''' The cog disabled check '''
        return utils.check_enabled(ctx)

def setup(bot):
    ''' Add cog to bot '''
    cog = Anime(bot)
    bot.add_cog(cog)
