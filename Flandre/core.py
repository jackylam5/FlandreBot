''' core.py
Written by jackylam5 and maware
- Load config file (config.json)
- Sets up the logger for the bot
- Log the bot on
- Set's the bot's game 
'''

import discord
import json
# Import Flandre Errors
from .errors import MissingConfigFile

class Bot(discord.ext.commands.Bot):

    def __init__(self):
        ''' Set up config and logging. Then set up the built-in discord bot '''
        self.config = None
        self.logger = None
        self.discordlogger = None
        self.loadConfig()
        self.makeLoggers()

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
                json.dump({'token': '', 'prefix': '!', 'description': "FlandreBot always a work in progress. Written by Jackylam5 and maware", 'pm_help': True, 'dev_mode': False})
            print("A config file has been made for you (Flandre/config.json). Please fill it out and restart the bot")
            # Raise MissingConfigFile to end the bot script
            raise MissingConfigFile

