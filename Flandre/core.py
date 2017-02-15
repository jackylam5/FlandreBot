''' core.py
Written by Scrubs (jackylam5 & maware)
- Load config file (config.json)
- Sets up the logger for the bot
- Log the bot on
- Set's the bot's game 
'''

import discord
from discord.ext import commands
import json
import logging
from logging.handlers import TimedRotatingFileHandler
# Import Flandre Errors
from .errors import MissingConfigFile

class Bot(commands.Bot):

    def __init__(self):
        ''' Set up config and logging. Then set up the built-in discord bot '''
        self.config = None
        self.logger = None
        self.discordlogger = None
        self.loadConfig()
        self.makeLoggers()

        # Check if config has a prefix
        if self.config['prefix'] == '':
            self.config['prefix'] = '!'
            self.logger.warning("Prefix in config was empty. Using '!' as the prefix")

        # Load the __init__ for commands.Bot with values in config 
        super().__init__(command_prefix = self.config['prefix'], description = self.config['description'], pm_help = self.config['pm_help'])

    def loadConfig(self):
        ''' Load the config file
        Raises Flandre.MissingConfigFile if file not found
        And makes the file for the user
        '''
        try:
            # Load config
            with open('Flandre/config.json', 'r') as config:
                self.config = json.load(config)
        except (json.decoder.JSONDecodeError, IOError) as e:
            # If config file is missing tell user and create one for them to fill out
            print("[!] Config File (Flandre/config.json) Missing")
            print("\tReason: {0}".format(e))
            with open('Flandre/config.json', 'w') as config:
                json.dump({'token': '', 'prefix': '!', 'description': "FlandreBot always a work in progress. Written by Jackylam5 and maware", 'pm_help': True, 'dev_mode': False}, config)
            print("A config file has been made for you (Flandre/config.json). Please fill it out and restart the bot")
            # Raise MissingConfigFile to end the bot script
            raise MissingConfigFile(e)


    def makeLoggers(self):
        ''' Makes the logger and log file 
        This makes a log file that holds all Flandre and discord.py errors
        It will be remade every monday
        '''
        
        # Make Flandre's logger
        self.logger = logging.getLogger('Flandre')
        self.logger.setLevel(logging.DEBUG)

        # Make discord.py's logger
        self.discordlogger = logging.getLogger('discord')
        # If dev mode is enabled make the discord logging display everything
        if self.config['dev_mode']:
            self.discordlogger.setLevel(logging.DEBUG)
        else:
            self.discordlogger.setLevel(logging.ERROR)
        
        # Make file handler for log file
        fh = TimedRotatingFileHandler(filename='Flandre.log', when='W0', interval=1, backupCount=5, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # Make the format for log file
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s > %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.discordlogger.addHandler(fh)