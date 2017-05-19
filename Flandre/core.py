''' core.py
Written by jackylam5 & maware
- Load config file (config.json)
- Sets up the logger for the bot
- Log the bot on
- Set's the bot's game 
'''

import discord
from discord.ext import commands
import logging
from logging.handlers import TimedRotatingFileHandler
import json
# Import Flandre Errors
from .errors import *
from . import utils


class Bot(commands.AutoShardedBot):

    def __init__(self):
        ''' Set up config and logging. Then set up the built-in discord bot 
        '''
        self.config = None
        self.logger = self.makeLogger()
        self.loadConfig()

        # Check if config has a prefix
        if self.config['prefix'] == '':
            self.config['prefix'] = '!'
            self.logger.warining("Prefix in config was empty. Using '!' as the prefix")

        # Load the __init__ for commands.Bot with values in config 
        super().__init__(command_prefix = commands.when_mentioned_or(self.config['prefix']), description = self.config['description'], pm_help = self.config['pm_help'])

    def makeLogger(self):
        ''' Make the logger for the bot
        '''

        # Make Flandre's logger
        logger = logging.getLogger(__package__)
        logger.setLevel(logging.DEBUG)

        # Make file handler for log file
        fh = TimedRotatingFileHandler(filename=f'{__package__}.log', when='d', interval=1, backupCount=5, encoding='utf-8')
        fh.setLevel(logging.DEBUG)

        # Make the format for log file
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s > [%(module)s.%(funcName)s] %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        return logger

    def loadConfig(self):
        ''' Load the config file
        Raises MissingConfigFile if file not found
        And makes the file for the user
        '''
        try:
            # Load config
            with open(f'{__package__}/config.json', 'r') as config:
                self.config = json.load(config)
        except (json.decoder.JSONDecodeError, IOError) as e:
            # If config file is missing tell user
            print(f"[!] Config File ({__package__}/config.json) Missing")
            print("\tReason: {0}".format(e))
            
            # Create new config file for user with defaults added in
            tempconfig = {'token': '', 'prefix': '!', "ownerid": [], 'description': "FlandreBot always a work in progress. Written by Jackylam5 and maware", 'pm_help': True, "game": "Help = !help", 'dev_mode': False}
            with open(f'{__package__}/config.json', 'w') as config:
                json.dump(tempconfig, config, indent=4, sort_keys=True)
            
            # Tell user config file was made and also log it
            print(f"A config file has been made for you ({__package__}/config.json). Please fill it out and restart the bot")
            self.logger.critical(f"Config File ({__package__}/config.json) Missing. It has been remade for you")
            
            # Raise MissingConfigFile to end the bot script
            raise MissingConfigFile(e)

    def run(self):
        '''Replace discord clients run command to inculde bot token from config
        If the token is empty or incorrect raises LoginError
        '''

        if self.config['token'] == '':
            print("Token is empty please open the config file and add your Bots token")
            self.logger.critical("Token is empty please open the config file and add your Bots token")
            raise LoginError()
        else:
            return super().run(self.config['token'])

    async def on_ready(self):
        ''' When bot has fully logged on 
        Log bots username and ID
        Then load cogs
        '''

        shardnumber = 1
        if self.shard_ids:
            shardnumber = len(self.shard_ids)
        self.logger.info(f'Logged in as: {self.user.name} ({self.user.id}) using {shardnumber} shards')
        await self.change_presence(game=discord.Game(name=self.config['game']))

