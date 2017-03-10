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
            with open('Flandre/data/mod/filter', 'w') as file:
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

def setup(bot):
    n = mod(bot)
    bot.add_cog(n)