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
from os import listdir, mkdir
from os.path import isdir
from sys import exit
import sys
# Import Flandre Errors
from .errors import *
from Flandre import permissions

class Reloader:
    ''' These commands are for bot owners only
    It allows you to reload/load/unload cogs
    '''

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def reload(self, ctx, *, module: str):
        '''Reload modules.'''
        
        # Get the message sent
        message = ctx.message

        # Log that the cog is being reloaded and by who
        self.bot.log('info', "Reload module: {0}. Requested by {1.name}#{1.discriminator}".format(module, message.author))
        
        try:
            # Get the module's cog and check it has a _unload function in it (Must be an async function)
            cog = self.bot.get_cog(module)
            unload_function = getattr(cog, "_unload", None)
            if unload_function is not None:
                self.bot.log('info', "Cog has a _unload function. Running it")
                await unload_function()

            self.reloadcog(module)
            self.bot.log('info', "Reloaded: {}".format(module))
            await self.bot.say("Done reloading: {}".format(module))
        except Exception as e:
            self.bot.log('critical', "Reload failed. Reason: {}".format(e))
            await self.bot.say("Something went wrong. Check log to see what it was")

            
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def load(self, ctx, *, module: str):
        '''Load modules.'''
        
        # Get the message sent
        message = ctx.message

        # Log that the cog is being loaded and by who
        self.bot.log('info', "Load module: {0}. Requested by {1.name}#{1.discriminator}".format(module, message.author))
        
        try:
            self.loadcog(module)
            self.bot.log('info', "Loaded: {}".format(module))
            await self.bot.say("Done loading: {}".format(module))

        except Exception as e:
            self.bot.log('critical', "Load failed. Reason: {}".format(e))
            await self.bot.say("Something went wrong. Check log to see what it was")
    
    @commands.command(pass_context=True)    
    @permissions.checkOwner()
    async def unload(self, ctx, *, module: str):
        '''Unload modules.'''
        
        # Get the message sent
        message = ctx.message

        # Log that the cog is being unloaded and by who
        self.bot.log('info', "Unload module: {0}. Requested by {1.name}#{1.discriminator}".format(module, message.author))

        try:
            # Get the module's cog and check it has a _unload function in it (Must be an async function)
            cog = self.bot.get_cog(module)
            unload_function = getattr(cog, "_unload", None)
            if unload_function is not None:
                self.bot.log('info', "Cog has a _unload function. Running it")
                await unload_function()

            self.unloadcog(module)
            self.bot.log('info', "Unloaded: {}".format(module))
            await self.bot.say("Done unloading: {}".format(module))

        except Exception as e:
            self.bot.log('critical', "Unload failed. Reason: {}".format(e))
            await self.bot.say("Something went wrong. Check log to see what it was")
    
    #reload function
    def reloadcog(self, cog):
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.unload_extension(cog)
        self.bot.load_extension(cog)
        
    def loadcog(self, cog):
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.load_extension(cog)
      
    def unloadcog(self, cog):
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.unload_extension(cog)


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
        super().__init__(command_prefix = commands.when_mentioned_or(self.config['prefix']), description = self.config['description'], pm_help = self.config['pm_help'])

    def log(self, logtype, message):
        ''' Log the info supplied by the user
        Requires the object that called it e.g the cog, the error type and the message to log
        The types of errors are:
            - info
            - warn
            - error
            - critical
        '''
        if logtype.lower() == 'info':
            self.logger.info("[{0.f_locals[self].__class__.__name__}.{0.f_code.co_name}] {1}".format(sys._getframe(1), message))
        elif logtype.lower() == 'warn':
            self.logger.warning("[{0.f_locals[self].__class__.__name__}.{0.f_code.co_name}] {1}".format(sys._getframe(1), message))
        elif logtype.lower() == 'error':
            self.logger.error("[{0.f_locals[self].__class__.__name__}.{0.f_code.co_name}] {1}".format(sys._getframe(1), message))
        elif logtype.lower() == 'critical':
            self.logger.critical("[{0.f_locals[self].__class__.__name__}.{0.f_code.co_name}] {1}".format(sys._getframe(1), message))
        else:
            self.logger.critical("Invalid log type suppiled > [{0.f_locals[self].__class__.__name__}.{0.f_code.co_name}] {1}".format(sys._getframe(1), message))

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
            tempconfig = {'token': '', 'prefix': '!', "ownerid": [], 'description': "FlandreBot always a work in progress. Written by Jackylam5 and maware", 'pm_help': True, "game": "Help = !help", 'dev_mode': False}
            with open('Flandre/config.json', 'w') as config:
                json.dump(tempconfig, config, indent=4, sort_keys=True)
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
        fh = TimedRotatingFileHandler(filename='Flandre.log', when='d', interval=1, backupCount=5, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # Make the format for log file
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s > %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.discordlogger.addHandler(fh)

    def start(self):
        '''Replace discord clients start command to inculde bot token from config
        If the token is empty or incorrect raises Flandre.LoginError
        '''

        if self.config['token'] == '':
            print("Token is empty please open the config file and add your Bots token")
            self.log("critical", "Token is empty please open the config file and add your Bots token")
            raise LoginError("Token is empty please open the config file and add your Bots token")
        else:
            return super().start(self.config['token'])

    async def on_ready(self):
        ''' When bot has fully logged on 
        Log bots username and ID
        Then load cogs
        '''

        self.log('info', 'Logged in as: {0.user.name} ({0.user.id})'.format(self))
        await self.change_presence(game=discord.Game(name=self.config['game']))

        # Add reload functions
        self.add_cog(Reloader(self))
        self.log('info', 'Loaded Cog: Reloader')

        # Check for data folder
        if not isdir('Flandre/data'):
            self.log('warn', "No Data folder found. It has been made for you at 'Flandre/data'")
            mkdir('Flandre/data')

        # Load cogs
        if isdir('Flandre/cogs'):
            files = [file for file in listdir('Flandre/cogs') if ".py" in file]
            if len(files) == 0:
                print("No python files found. Which means no commands found. Bot logged off")
                self.log('critical', "No python files found. Which means no commands found. Bot logged off")
                await self.logout()
                exit("No python files found. Which means no commands found. Bot logged off")
            else:
                for file in files:
                    self.log('info', "Loaded Cog: {}".format(file[:-3]))
                    self.load_extension('Flandre.cogs.' + file[:-3])
        else:
            mkdir('Flandre/cogs')
            print("No cog folder found. Which means no commands found. Bot logged off")
            self.log('critical', "No cog folder found. Which means no commands found. Bot logged off")
            self.log('info', "Flandre/cogs has been made for you")
            print("Flandre/cogs has been made for you")
            await self.logout()
            exit("No cog folder found. Which means no commands found. Bot logged off")

