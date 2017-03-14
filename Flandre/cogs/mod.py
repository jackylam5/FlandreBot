import discord
from discord.ext import commands
from Flandre import permissions
from os import mkdir
from os.path import isdir
import json

class mod:
    '''Moderation tools
    '''

    def __init__(self, bot):
        self.bot = bot
        self.logging_channels = {}
        self.past_names = {}
        self.filter = {}
        self.ignore_list = {}
        self.loadFiles()

    def loadFiles(self):
        '''Loads the files for the cog stored in cog data folder
        '''
        if not isdir('Flandre/data/mod'):
            # Make the directory if missing and the files that go with it 
            self.bot.log('warn', 'Cogs data folder not found, it and all files have been made')

            mkdir('Flandre/data/mod')
            with open('Flandre/data/mod/logging_channels.json', 'w') as file:
                json.dump({}, file)
            with open('Flandre/data/mod/past_names.json', 'w') as file:
                json.dump({}, file)
            with open('Flandre/data/mod/filter.json', 'w') as file:
                json.dump({}, file)
            with open('Flandre/data/mod/ignore_list.json', 'w') as file:
                json.dump({}, file)
        else:
            # Check for logging_channels file
            try:
                with open('Flandre/data/mod/logging_channels.json', 'r') as file:
                    self.logging_channels = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.logging_channels = {}
                self.bot.log('error', 'logging_channels.json could not be loaded. Reason: {0}'.format(e))
                
                # Make the file for user again
                with open('Flandre/data/mod/logging_channels.json', 'w') as file:
                    json.dump({}, file)
                self.bot.log('info', 'Flandre/data/mod/logging_channels.json has been remade for you')
            
            # Check for past_names file
            try:
                with open('Flandre/data/mod/past_names.json', 'r') as file:
                    self.past_names = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.past_names = {}
                self.bot.log('error', 'past_names.json could not be loaded. Reason: {0}'.format(e))
                
                # Make the file for user again
                with open('Flandre/data/mod/past_names.json', 'w') as file:
                    json.dump({}, file)
                self.bot.log('info', 'Flandre/data/mod/past_names.json has been remade for you')

            # Check for filter file
            try:
                with open('Flandre/data/mod/filter.json', 'r') as file:
                    self.filter = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.filter = {}
                self.bot.log('error', 'filter.json could not be loaded. Reason: {0}'.format(e))
                
                # Make the file for user again
                with open('Flandre/data/mod/filter.json', 'w') as file:
                    json.dump({}, file)
                self.bot.log('info', 'Flandre/data/mod/filter.json has been remade for you')

            # Check for ignore_list file
            try:
                with open('Flandre/data/mod/ignore_list.json', 'r') as file:
                    self.ignore_list = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.ignore_list = {}
                self.bot.log('error', 'ignore_list.json could not be loaded. Reason: {0}'.format(e))
                
                # Make the file for user again
                with open('Flandre/data/mod/ignore_list.json', 'w') as file:
                    json.dump({}, file)
                self.bot.log('info', 'Flandre/data/mod/ignore_list.json has been remade for you')

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def logchannel(self, ctx):
        '''Sets the channel command is typed in as the log channel for that server
        '''
        removed = False
        if ctx.message.server.id in self.logging_channels:
            self.logging_channels.pop(ctx.message.server.id)
            removed = True
        else:
            self.logging_channels[ctx.message.server.id] = ctx.message.channel.id
        
        try:
            with open('Flandre/data/mod/logging_channels.json', 'w') as file:
                json.dump(self.logging_channels, file, indent=4, sort_keys=True)
        except:
            if removed:
                await self.bot.say('This channel is no longer the log channel for the mod actions. However is couldn\'t be save for some reason')
            else:
                await self.bot.say('This channel has been made the log channel for the mod actions. However is couldn\'t be save for some reason')
            self.bot.log('critical', 'Flandre/data/mod/logging_channels.json could not be saved. Please check it')
        else:
            if removed:
                await self.bot.say('This channel is no longer the log channel for the mod actions.')
                self.bot.log('info', 'Flandre/data/mod/logging_channels.json has been saved. Reason: {0.name} ({0.id}) is no longer a logging channel'.format(ctx.message.channel))
            else:
                await self.bot.say('This channel has been made the log channel for the mod actions.')
                self.bot.log('info', 'Flandre/data/mod/logging_channels.json has been saved. Reason: {0.name} ({0.id}) has been made a logging channel'.format(ctx.message.channel))
            

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkMod()
    async def kick(self, ctx, user : discord.Member, reason : str = ""):
        ''' Kicks the user mentioned with reason
            If server has log channel it is logged
        '''
        author = ctx.message.author
        try:
            await self.bot.kick(user)
            await self.bot.say("Done. User kicked for reason: `{0}`".format(reason))
        except discord.errors.Forbidden:
            await self.bot.say("Can't do that user has higher role than me")
        except discord.errors.HTTPException:
            await self.bot.say("Something went wrong. Please try again")
        else:
            if ctx.message.server.id in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[ctx.message.server.id])
                await self.bot.send_message(log_channel, '{0.mention} has kicked {1.mention}!\nReason: `{2}`'.format(author, user, reason))

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def ban(self, ctx, user : discord.Member, reason : str = "", days : int = 0):
        ''' Bans the user mentioned with reason, number of days to delete message comes after
            If server has log channel it is logged
        '''

        author = ctx.message.author
        try:
            await self.bot.ban(user, days)
            await self.bot.say("Done. User banned for reason: `{0}`".format(reason))
        except discord.errors.Forbidden:
            await self.bot.say("Can't do that user has higher role than me")
        except discord.errors.HTTPException:
            await self.bot.say("Something went wrong. Please try again")
        else:
            if ctx.message.server.id in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[ctx.message.server.id])
                await self.bot.send_message(log_channel, '{0.mention} has banned {1.mention}!\nReason: `{2}`'.format(author, user, reason))

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkMod()
    async def softban(self, ctx, user : discord.Member, reason : str = ""):
        ''' Softbans the user mentioned with reason. Uses as a kick that cleans up mesages
            If server has a log channel it is logged
        '''
        author = ctx.message.author
        server = ctx.message.server
        try:
            await self.bot.ban(user, 1)
            await self.bot.unban(server, user)
            await self.bot.say("Done. User softbanned for reason: `{0}`".format(reason))
        except discord.errors.Forbidden:
            await self.bot.say("Can't do that user has higher role than me")
        except discord.errors.HTTPException:
            await self.bot.say("Something went wrong. Please try again")
        else:
            if ctx.message.server.id in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[ctx.message.server.id])
                await self.bot.send_message(log_channel, '{0.mention} has softbanned {1.mention}!\nReason: `{2}`'.format(author, user, reason))

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkMod()
    async def rename(self, ctx, user : discord.Member, *, nickname : str = ''):
        ''' Renames the mentioned user. No nickname given removes it
        '''

        if nickname == '':
            nickname = None
        else:
            nickname = nickname.strip()

        try:
            await self.bot.change_nickname(user, nickname)
            await self.bot.say("Users Nickname has been changed")
        except discord.errors.Forbidden:
            await self.bot.say("I can't do that. I lack the permissions to do so")
        except dscord.errors.HTTPException:
            await self.bot.say("Something went wrong. Please try again")

    @commands.group(pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def cleanup(self, ctx):
        ''' Deletes messages

            cleanup messages [number] - removes number amount of messages
            cleanup user [name/mention] [number] - remove number amount of users messages
            cleanup text "Text" [number] - removes number amount of messages with text in it
        '''

        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.send_message(ctx.message.channel, page)

    @cleanup.command(no_pm=True, pass_context=True)
    async def text(self, ctx, text : str, number : int):
        ''' Deletes the last X messages containing the text specified
            Double quotes are needed for the text string

            Example: cleanup text "Test" 5
        '''

        while deleted != number:



def setup(bot):
    n = mod(bot)
    bot.add_cog(n)