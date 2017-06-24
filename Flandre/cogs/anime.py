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

class Anime:
    '''
    Cog that has all anime and manga related items.
    Uses the anilist api to get info about that anime/manga
    Works using time in Japan (GMT+9)
    '''

    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    ''' Add cog to bot '''
    cog = Anime(bot)
    bot.add_cog(cog)