''' core.py
Written by jackylam5 & maware
- Load config file (config.json)
- Sets up the logger for the bot
- Log the bot on
- Set's the bot's game
'''

import datetime
import json
import logging
import os
import sys

import discord
from discord.ext import commands

from . import utils
from .errors import CogDisabled, LoginError, MissingConfigFile

logger = logging.getLogger(__name__)

class Bot(commands.AutoShardedBot):
    '''
    A custom subclass of Discord.py's Bot Class
    '''

    def __init__(self):
        ''' Set up config and logging. Then set up the built-in discord bot '''
        self.config = None
        self.start_time = datetime.datetime.utcnow()
        self.load_config()

        # Check if config has a prefix
        if self.config['prefix'] == '':
            self.config['prefix'] = '!'
            logger.warining("Prefix in config was empty. Using '!' as the prefix")

        # Load the __init__ for commands.Bot with values in config
        super().__init__(command_prefix=commands.when_mentioned_or(self.config['prefix']),
                         description=self.config['description'],
                         pm_help=self.config['pm_help'])

    @property
    def uptime(self):
        ''' Gets the uptime for the bot '''
        return datetime.datetime.utcnow() - self.start_time

    def load_config(self):
        ''' Load the config file
        Raises MissingConfigFile if file not found
        And makes the file for the user
        '''
        try:
            # Load config
            with open('Flandre/config.json', 'r') as config:
                self.config = json.load(config)
        except (json.decoder.JSONDecodeError, IOError) as err:
            # If config file is missing tell user
            print("[!] Config File (Flandre/config.json) Missing")
            print("\tReason: {0}".format(err))

            # Create new config file for user with defaults added in
            tempconfig = {'token': '',
                          'prefix': '!',
                          'ownerid': [],
                          'description': ('FlandreBot always a work in progress. '
                                          'Written by Jackylam5 and maware'),
                          'pm_help': True,
                          'game': 'scrub',
                          'use_avconv': True
                         }

            with open('Flandre/config.json', 'w') as config:
                json.dump(tempconfig, config, indent=4, sort_keys=True)

            # Tell user config file was made and also log it
            print(("A config file has been made for you (Flandre/config.json). "
                   "Please fill it out and restart the bot"))

            logger.critical(("Config File (Flandre/config.json) "
                             "Missing. It has been remade for you"))

            # Raise MissingConfigFile to end the bot script
            raise MissingConfigFile(err)

    def run(self):
        '''Replace discord clients run command to inculde bot token from config
        If the token is empty or incorrect raises LoginError
        '''

        if self.config['token'] == '':
            err_msg = 'Token is empty please open the config file and add your Bots token'
            print(err_msg)
            logger.critical(err_msg)
            raise LoginError()
        else:
            return super().run(self.config['token'])

    async def on_ready(self):
        ''' When bot has fully logged on
        Log bots username and ID
        Then load cogs
        '''

        # Tell user bot has logged in with how many shards
        logger.info(('Logged in as: '
                     f'{self.user.name} ({self.user.id}) using {self.shard_count} shards'))

        # Change the bots game to what is in the config
        await self.change_presence(game=discord.Game(name=self.config['game']))

        # Check for data and cog foders
        utils.check_core_folders()

        # Load the owner reloader and Cogdisable
        self.add_cog(utils.Reloader(self))
        logger.info('Loaded cog: Reloader')
        self.add_cog(utils.Cogdisable(self))
        logger.info('Loaded cog: Cogdisable')

        # Load cogs
        files = [cog for cog in os.listdir('Flandre/cogs') if utils.check_if_cog(cog)]

        if files:
            for file in files:
                try:
                    self.load_extension(f'Flandre.cogs.{file}')

                except Exception as err:
                    # Something made the loading fail
                    # So log it with reason and tell user to check it
                    logger.critical(f'Load failed for {file}. Reason: {err}')
                    continue

                else:
                    logger.info(f'Loaded cog: {file}')
        else:
            err_msg = "No cogs found. Which means no commands found. Bot logged off"
            print(err_msg)
            logger.critical(err_msg)
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

        elif isinstance(error, CogDisabled):
            # The cog was disabled
            await ctx.send('The cog this command is in has been '
                           'disabled for this guild')

        elif isinstance(error, commands.errors.CheckFailure):
            # Tell the user they do not have permission to use that command
            await ctx.send(('You are not able to run this command '
                            'due to your permissions'))

        elif isinstance(error, commands.errors.BadArgument):
            # Tell the user there was a bad argument
            await ctx.send('Ya fooked up m8')

        else:
            # Log any other errors
            logger.exception('Command "%s". Message "%s"',
                             ctx.command,
                             ctx.message.content,
                             exc_info=error.original)
