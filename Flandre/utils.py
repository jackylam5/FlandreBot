''' utils.py
Holds the reloading cog and the function to save stuff to the data folder for cogs easily
'''

import json
import logging
from os import mkdir
from os.path import isdir, isfile

import discord
from discord.ext import commands

from . import permissions, errors

logger = logging.getLogger(__name__)

class Cogdisable:
    ''' Allows guilds to disable certain cogs '''

    def __init__(self, bot):
        self.bot = bot
        # Make a json file that holds the guild id with the cogs disabled if not found
        if not isfile('Flandre/cogs/disabled_cogs.json'):
            with open('Flandre/cogs/disabled_cogs.json', 'w') as file:
                json.dump({}, file, indent=4, sort_keys=True)

    @commands.group(name='cog')
    @commands.guild_only()
    @permissions.check_admin()
    async def _cog(self, ctx):
        '''
        Group of commands to cog actions.
        Such as enable and disable
        '''

        if ctx.invoked_subcommand is None:
            pages = await send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @_cog.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def disable(self, ctx, cog_name: str):
        '''
        Disables the cog given for the guild so it can not be used
        '''

        if cog_name.title() != 'Cogdisable' and cog_name.title() != 'Reloader':
            # Check if the cog is even loaded/valid
            if cog_name.title() in self.bot.cogs:
                # Load the data file
                with open('Flandre/cogs/disabled_cogs.json', 'r+') as file:
                    data = json.load(file)

                    # Check if the guild is already disabling cogs
                    # If not add it too the file
                    if str(ctx.guild.id) not in data:
                        data[str(ctx.guild.id)] = []

                    # Check if cog is already disabled
                    if cog_name.title() in data[(str(ctx.guild.id))]:
                        await ctx.send('That cog is already disabled for this guild')

                    else:
                        data[str(ctx.guild.id)].append(cog_name.title())

                        # Clear the file before saving
                        file.seek(0)
                        file.truncate()

                        json.dump(data, file, indent=4, sort_keys=True)
                        await ctx.send('Cog is now disabled')
            else:
                await ctx.send("That cog hasn't been loaded or isn't vaild")

        else:
            await ctx.send("You can't disable that cog it is needed")

    @_cog.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def enable(self, ctx, cog_name: str):
        '''
        Enables the cog given for the guild so it can be used again
        '''

        # Check if the cog is even loaded/valid
        if cog_name.title() in self.bot.cogs:
            # Load the data file
            with open('Flandre/cogs/disabled_cogs.json', 'r+') as file:
                data = json.load(file)

                # Check if cog is disabled
                if cog_name.title() in data[(str(ctx.guild.id))]:
                    data[str(ctx.guild.id)].remove(cog_name.title())

                    # Check if the guild can be removed from the file
                    if not data[str(ctx.guild.id)]:
                        del data[str(ctx.guild.id)]

                    # Clear the file before saving
                    file.seek(0)
                    file.truncate()

                    json.dump(data, file, indent=4, sort_keys=True)
                    await ctx.send('Cog is now enabled')

                else:
                    await ctx.send("That cog isn't disabled for this guild")
        else:
            await ctx.send("That cog hasn't been loaded or isn't vaild")

    @_cog.command()
    @commands.guild_only()
    async def show(self, ctx):
        '''
        Lists the cogs showing what ones are disabled for the guild
        '''

        # Load the data file
        with open('Flandre/cogs/disabled_cogs.json', 'r') as file:
            data = json.load(file)

        # Set data to only the guild's data if any
        if str(ctx.guild.id) in data:
            data = data[str(ctx.guild.id)]
        else:
            data = []

        msg = 'Cogs: ```'

        # Loop over all the cogs and tell user what is disabled
        for cog in self.bot.cogs:
            if cog == 'Cogdisable' or cog == 'Reloader':
                continue

            if cog in data:
                msg += f'{cog} [DISABLED]\n'

            else:
                msg += f'{cog} [ENABLED]\n'

            if len(msg) > 1500:
                msg += '```'
                await ctx.send(msg)
                msg = '```'

        msg += '```'
        await ctx.send(msg)

class Reloader:
    ''' Allows owners to load/unload/reload cogs easily '''

    def __init__(self, bot):
        self.bot = bot

    def loadcog(self, cog):
        ''' Load cog/module '''
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.load_extension(cog)

    def unloadcog(self, cog):
        ''' Unload cog/module '''
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.unload_extension(cog)

    @commands.command()
    @permissions.check_owners()
    async def load(self, ctx, module: str):
        ''' Load modules/cogs into the bot.
        '''

        # Log that a module/cog has been requested to be loaded
        logger.info((f'Load module/cog: {module}. '
                     f'Requested by {ctx.author.name}#{ctx.author.discriminator}'))

        # Load cog
        try:
            self.loadcog(module)

        except Exception as err:
            # Something made the loading fail so log it with reason and tell user to check it
            logger.critical(f'Load failed. Reason: {err}')
            await ctx.send('Something went wrong loading the cog. Check log to see what it was')

        else:
            # The cog loaded so we log that it was loaded and also tell the user
            logger.info(f'Loaded cog: {module}')
            await ctx.send(f'Loaded cog: {module}')

    @commands.command()
    @permissions.check_owners()
    async def unload(self, ctx, module: str):
        ''' Unload modules/cogs from the bot.
        '''

        # Log that a module/cog has been requested to be unloaded
        logger.info((f'Unload module/cog: {module}. '
                     f'Requested by {ctx.author.name}#{ctx.author.discriminator}'))

        # Unload cog
        try:
            self.unloadcog(module)

        except Exception as err:
            # Something made the unloading fail so log it with reason and tell user to check it
            logger.critical(f'Unload failed. Reason: {err}')
            await ctx.send('Something went wrong unloading the cog. Check log to see what it was')

        else:
            # The cog unloaded so we log that it was unloaded and also tell the user
            logger.info(f'Unloaded cog: {module}')
            await ctx.send(f'Unloaded cog: {module}')

    @commands.command()
    @permissions.check_owners()
    async def reload(self, ctx, module: str):
        ''' Reload modules/cogs the bot has.
        '''

        # Log that a module/cog has been requested to be reloaded
        logger.info((f'Reload module/cog: {module}. '
                     f'Requested by {ctx.author.name}#{ctx.author.discriminator}'))

        # Reload cog
        try:
            self.unloadcog(module)
            self.loadcog(module)

        except Exception as err:
            # Something made the reload fail so log it with reason and tell user to check it
            logger.critical(f'Reload failed. Reason: {err}')
            await ctx.send('Something went wrong reloading the cog. Check log to see what it was')

        else:
            # The cog unloaded so we log that it was unloaded and also tell the user
            logger.info(f'Reloaded cog: {module}')
            await ctx.send(f'Reloaded cog: {module}')

def check_core_folders():
    ''' Used to check if the bot has a cogs and data folder
    '''

    # Check for cogs folder
    if not isdir('Flandre/cogs'):
        logger.warning("No cogs folder found. It has been made for you at 'Flandre/cogs'")
        mkdir('Flandre/cogs')

async def send_cmd_help(bot, ctx):
    ''' Make the formatting for command groups from context '''
    if ctx.invoked_subcommand:
        pages = await bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)

    else:
        pages = await bot.formatter.format_help_for(ctx, ctx.command)

    return pages

def check_enabled(ctx):
    ''' Check if cog is enabled do be done in local check '''
    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return True

    # Load the data file
    with open('Flandre/cogs/disabled_cogs.json', 'r') as file:
        data = json.load(file)

    # Check if guild is even disabling anything
    if str(ctx.guild.id) in data:
        cog_name = ctx.command.cog_name

        # Check if cog is disabled
        if cog_name in data[str(ctx.guild.id)]:
            raise errors.CogDisabled

        else:
            return True
    else:
        return True

def check_if_cog(cog):
    ''' Checks if the cog is a folder and does not start with _ '''

    return cog[0] != '_' and isdir(f'Flandre/cogs/{cog}')
