'''
Core Bot file
Handles all discord events such as:
    - Message received
    - Bot joins a server
    - Member joins a server
'''
import discord
import json
import logging
from discord.ext import commands
import glob
import os


class BOT(commands.Bot):

    def __init__(self):
        self.logger = None
        self.discordlogger = None
        self.makeLogger()
        self.config = {}
        self.loadConfig()
        super().__init__(command_prefix = self.config['prefix'], description = self.config['description'])

    def makeLogger(self):
        ''' Makes the logger and log file '''
        # Make Flandre's logger
        self.logger = logging.getLogger('Flandre')
        self.logger.setLevel(logging.DEBUG)

        # Make discord.py's logger
        self.discordlogger = logging.getLogger('discord')
        self.discordlogger.setLevel(logging.INFO)
        
        # Make file handler for log file
        fh = logging.FileHandler(filename='Flan.log', encoding='utf-8', mode='w')
        fh.setLevel(logging.DEBUG)
        
        # Make the format for log file
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.discordlogger.addHandler(fh)

    def loadConfig(self):
        ''' Load the config from the config.json file '''
        try:
            with open('FlandreBot/config.json', 'r') as config:
                self.logger.info('Loaded FlandreBot\config.json')
                self.config = json.load(config)
        except json.decoder.JSONDecodeError:
            self.logger.error('FlandreBot\config.json could not be loaded (JSON Decode Error)')

    def start(self):
        ''' Replace discord clients start command to inculde bot token from config '''
        return super().start(self.config['token'])

    async def on_ready(self):
        ''' When bot has fully logged on '''
        print('[*] Logged in as: {0.user.name} ({0.user.id}).'.format(self))
        self.logger.info('Logged in as: {0.user.name} ({0.user.id})'.format(self))     
        owd = os.getcwd()
        os.chdir("FlandreBot/cogs")
        for file in glob.glob("*.py"):
            os.chdir(owd)
            self.load_extension('FlandreBot.cogs.' + file[:-3] + '')
            os.chdir("FlandreBot/cogs")
        os.chdir(owd)
        
        
