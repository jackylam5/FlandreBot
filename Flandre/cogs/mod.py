import discord
from discord.ext import commands
from Flandre import permissions
from os import mkdir
from os.path import isdir
import json
import asyncio
import re

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

    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages
                
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
                await self.bot.send_message(ctx.message.channel, page)

    @cleanup.command(no_pm=True, pass_context=True)
    async def text(self, ctx, text : str, number : int = 1):
        ''' Deletes the last X messages containing the text specified
            Double quotes are needed for the text string

            Example: cleanup text "Test" 5
        '''
        
        channel = ctx.message.channel
        message = ctx.message
        deleted = 0
        try:
            await self.bot.delete_message(message)
            await asyncio.sleep(0.25)
            while number > 0:
                async for logMessage in self.bot.logs_from(channel, limit = 10, before = message):
                    # Check if text is in the message then remove it.
                    if text in logMessage.content:
                        await self.bot.delete_message(logMessage)
                        await asyncio.sleep(0.25)
                        number -= 1
                        message = logMessage
                        deleted += 1
                    if number == 0:
                        break
            if ctx.message.server.id in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[ctx.message.server.id])
                await self.bot.send_message(log_channel, '{0} messages have been removed!'.format(deleted))
        except discord.errors.Forbidden:
            await self.bot.say("I can't do that. I lack the permissions to do so")
                        
    @cleanup.command(no_pm=True, pass_context=True)
    async def user(self, ctx, user : discord.Member, number : int = 1):
        ''' Deletes the last X messages from specified user
            
            Example:
            cleanup user @name 2
            cleanup user name 2
        '''
        
        channel = ctx.message.channel
        message = ctx.message
        deleted = 0
        
        try:
            await self.bot.delete_message(message)
            await asyncio.sleep(0.25)
            while number > 0:
                async for logMessage in self.bot.logs_from(channel, limit = 10, before = message):
                    # Check if the author of the message is the specified user then remove the message.
                    if logMessage.author.id in user.id:
                        await self.bot.delete_message(logMessage)
                        await asyncio.sleep(0.25)
                        number -= 1
                        message = logMessage
                        deleted += 1
                    if number == 0:
                        break
            if ctx.message.server.id in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[ctx.message.server.id])
                await self.bot.send_message(log_channel, '{0} messages have been removed!'.format(deleted))
        except discord.erros.Forbidden:
            await self.bot.say("I can't do that. I lack the permissions to do so")

    @cleanup.command(no_pm=True, pass_context=True)
    async def messages(self, ctx, number : int = 1):
        ''' Deletes the last X messages from specified user
            
            Example: cleanup messages 2
        '''
        
        channel = ctx.message.channel
        message = ctx.message
        deleted = 0
        
        try:
            await self.bot.delete_message(message)
            await asyncio.sleep(0.25)
            async for logMessage in self.bot.logs_from(channel, limit = number, before = message):
                await self.bot.delete_message(logMessage)
                await asyncio.sleep(0.25)
                deleted += 1
                
            if ctx.message.server.id in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[ctx.message.server.id])
                await self.bot.send_message(log_channel, '{0} messages have been removed!'.format(deleted))
        except discord.erros.Forbidden:
            await self.bot.say("I can't do that. I lack the permissions to do so")

    @commands.group(name='filter', pass_context=True, no_pm=True)
    async def _filter(self, ctx):
        ''' Adds or removes words from the filter
            It ignores case and will also remove the word if it is contained in another
            It can also remove full sentences if needed
        '''
        
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @_filter.command(name='show', pass_context=True, no_pm=True)
    async def filter_show(self, ctx):
        ''' Shows the current words/sentences in the filter
            Shows each on a single line will also send mutiple messages if needed
        '''

        # Check if the server has words being filtered
        if ctx.message.server.id in self.filter:
            # Make message and loop over each word being filtered
            msg = '```\n'
            for filtered in self.filter[ctx.message.server.id]:
                msg += '{0}\n'.format(filtered)
                # If the length of the messages is greater than 1600 send it and make another message for the rest
                if len(msg) > 1600:
                    msg += '```'
                    await self.bot.say(msg)
                    msg = '```\n'
            # Send message
            msg += '```'
            await self.bot.say(msg)
        else:
            await self.bot.say('Nothing is being filtered in this server')

    @_filter.command(name='add', pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def filter_add(self, ctx, *words : str):
        ''' Adds words or sentences to the filter
            Make sure to use double quotes for sentences
            Examples:
            filter add word1 word2 word3
            filter add "This is a sentence"
        '''

        words_added = False # Used just to know if the file is to be saved
        # Check if any words were suppiled
        if words:
            if ctx.message.channel.permissions_for(ctx.message.server.me).manage_messages:
                if ctx.message.server.id not in self.filter:
                    self.filter[ctx.message.server.id] = []
                    self.bot.log('info', 'Server {0.name} ({0.id}) has been added to the filter'.format(ctx.message.server))
                # Loop over each word in words
                for word in words:
                    # Check if word is already being filtered if it is just ignore it
                    if word in self.filter[ctx.message.server.id]:
                        continue
                    else:
                        self.filter[ctx.message.server.id].append(word)
                        words_added = True
                # Save the file if needed
                if words_added:
                    with open('Flandre/data/mod/filter.json', 'w') as file:
                        json.dump(self.filter, file)
                    self.bot.log('info', 'Flandre/data/mod/filter.json has been saved. Reason: {0.name} ({0.id}) has added words to filter'.format(ctx.message.server))
                # Send message saying words have been added
                await self.bot.say('Words have been added to the filter')
            else:
                await self.bot.say('{0}, I don\'t have the permissions to delete messages so I can filter anything')
        else:
            await self.bot.say('{0} you need to give me something to filter'.format(ctx.message.author.mention))

    @_filter.command(name='remove', pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def filter_remove(self, ctx, *words : str):
        ''' Removes words or sentences to the filter
            Make sure to use double quotes for sentences
            Examples:
            filter remove word1 word2 word3
            filter remove "This is a sentence"
        '''

        words_removed = False # Used just to know if the file is to be saved
        # Check if any words were suppiled
        if words:
            # Check if there is anything to remove
            if ctx.message.server.id in self.filter:
                # Loop over words
                for word in words:
                    if word not in self.filter[ctx.message.server.id]:
                        continue
                    else:
                        self.filter[ctx.message.server.id].remove(word)
                        words_removed = True
                # Check if the filter for that server is empty if so remove it
                if len(self.filter[ctx.message.server.id]) == 0:
                    self.filter.pop(ctx.message.server.id)
                    self.bot.log('info', 'Server {0.name} ({0.id}) has been removed from the filter'.format(ctx.message.server))
                # Save the file is needed
                if words_removed:
                    with open('Flandre/data/mod/filter.json', 'w') as file:
                        json.dump(self.filter, file)
                    self.bot.log('info', 'Flandre/data/mod/filter.json has been saved. Reason: {0.name} ({0.id}) has removed words from filter'.format(ctx.message.server))
                # Send message saying words have been added
                await self.bot.say('Words have been removed from the filter')
            else:
                await self.bot.say('Nothing is being filtered in this server to be removed')
        else:
            await self.bot.say('{0} you need to give me words to remove from the filter'.format(ctx.message.author.mention))

    def filter_immune(self, message):
        ''' Check if user can not be filtered
        '''

        # Check if bot owner
        if message.author.id in self.bot.config['ownerid']:
            return True
        elif message.author.permissions_in(message.channel).manage_server:
            # Admin in server
            return True
        elif message.author.permissions_in(message.channel).manage_channels:
            # Mod in server
            return True

    async def check_filter(self, message):
        ''' Check if the message contains a filtered word from a server
        '''

        # Check that the message was not a DM
        if not message.channel.is_private:
            # Double check bot can delete messages in server
            if message.channel.permissions_for(message.server.me).manage_messages:
                # Check the sever has words in filter
                if message.server.id in self.filter:
                    # Check user is not immune from filter
                    if not self.filter_immune(message):
                        # Loop over everything in server filter
                        for word in self.filter[message.server.id]:
                            found = re.search(word, message.content, re.IGNORECASE)
                            # If re found the word delete it and tell the user
                            if found is not None:
                                await self.bot.delete_message(message)
                                await self.bot.send_message(message.channel, "{0}, Oi that had a word that's not allowed in here. Don't do that".format(message.author.mention))
                                break

def setup(bot):
    n = mod(bot)
    bot.add_listener(n.check_filter, "on_message")
    bot.add_cog(n)