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
from logging.handlers import RotatingFileHandler
import json
from os import listdir
import sys
# Import Flandre Errors
from .errors import *
from . import utils

def when_mentioned_with_prefix(prefix):
    ''' Used to make the trigger for the bot a mention then a prefix you set
        e.g. @bot !help 
    '''    
    
    def inner(bot, msg):
        r = commands.when_mentioned(bot, msg)[0] + str(prefix)
        print(r)
        return r

    return inner

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
        super().__init__(command_prefix=when_mentioned_with_prefix(self.config['prefix']), description = self.config['description'], pm_help = self.config['pm_help'])


    def makeLogger(self):
        ''' Make the logger for the bot
        '''

        # Make Flandre's logger
        logger = logging.getLogger(__package__)
        logger.setLevel(logging.DEBUG)

        # Make file handler for log file
        fh = RotatingFileHandler(filename=f'{__package__}.log', mode='a', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8', delay=0)
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
            tempconfig = {'token': '', 'prefix': '!', "ownerid": [], 'description': "FlandreBot always a work in progress. Written by Jackylam5 and maware", 'pm_help': True, "game": "scrub", 'dev_mode': False}
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

        # Tell user bot has logged in with how many shards
        shardnumber = 1
        if self.shard_ids:
            shardnumber = len(self.shard_ids)
        self.logger.info(f'Logged in as: {self.user.name} ({self.user.id}) using {shardnumber} shards')
        
        # Change the bots game to what is in the config
        await self.change_presence(game=discord.Game(name=self.config['game']))

        # Load the owner reloader 
        self.add_cog(utils.reloader(self))
        self.logger.info('Loaded cog: reloader')

        # Check for data and cog foders
        utils.checkCoreFolders(self.logger)

        # Load cogs
        files = [file.replace('.py', '') for file in listdir(f'{__package__}/cogs') if ".py" in file]

        if files:
            for file in files:
                try:
                    self.load_extension(f'{__package__}.cogs.{file}')

                except Exception as e:
                    # Something made the loading fail so log it with reason and tell user to check it
                    self.logger.critical(f'Load failed for {file}. Reason: {e}')
                    continue
                
                else:
                    self.logger.info(f'Loaded cog: {file}')
        else:
            print("No python files found. Which means no commands found. Bot logged off")
            self.logger.critical("No python files found. Which means no commands found. Bot logged off")
            await self.logout()
            sys.exit()

    async def on_message(self, message):
        ''' Make sure other bots can not trigger the bot
        '''
        
        # Check the user is not a bot
        if not message.author.bot:        
            await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        '''Deals with errors when a command is invoked.
        '''

        if isinstance(error, commands.errors.CommandNotFound):
            # Ignore No command found as we don't care if it wasn't one of our commands
            pass

        elif isinstance(error, commands.errors.MissingRequiredArgument):
            # Tell the user they are missing a required argument
            await ctx.send(f'Argument `{error.param}` missing')

        elif isinstance(error, commands.errors.NoPrivateMessage):
            # Tell the user the command can not be done in a private message
            await ctx.send('Command can\'t be used in a Private Message')

        elif isinstance(error, commands.errors.CheckFailure):
            # Tell the user they do not have permission to use that command
            await ctx.send('You do not have permission to execute that command')

        elif isinstance(error, commands.errors.BadArgument):
            # Tell the user there was a bad argument
            await ctx.send('Arguement error')

        else:
            # Log any other errors
            self.bot.logger.exception('Command "%s". Message "%s"', ctx.command, ctx.message.content, exc_info=error.original)
