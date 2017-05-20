import discord
from discord.ext import commands
import datetime
import asyncio
from .. import permissions, utils
import re
from string import punctuation as asciipunct

class mod:
    ''' Moderation tools
    '''

    def __init__(self, bot):
        self.bot = bot
        self.logging_channels = utils.checkCogConfig(self, 'logging_channels.json')
        self.filter = utils.checkCogConfig(self, 'filter.json')

    def __unload(self):
        ''' Remove listeners
        '''

        self.bot.remove_listener(self.check_filter, "on_message")
        self.bot.remove_listener(self.check_edit_filter, "on_message_edit")

    def cleanReason(self, reason):
        ''' Removeds ` from the reason to stop escaping and format mentions if in reason
        '''

        reason = reason.replace('`', '')

        matches = re.findall('(<@!?(\d*)>)', reason)
        
        for match in matches:
            user = self.bot.get_user(int(match[1]))
            reason = reason.replace(match[0], f'@{user.name}#{user.discriminator}')

        return reason


    @commands.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def logchannel(self, ctx):
        '''Sets the channel command is typed in as the log channel for that server
        '''
        removed = False
        if str(ctx.guild.id) in self.logging_channels:
            self.logging_channels.pop(str(ctx.guild.id))
            removed = True
        else:
            self.logging_channels[str(ctx.guild.id)] = ctx.channel.id
        
        utils.saveCogConfig(self, 'logging_channels.json', self.logging_channels)
            
        if removed:
            await ctx.send('This channel is no longer the log channel for the mod actions.')
        else:
            await ctx.send('This channel has been made the log channel for the mod actions.')
    
    @commands.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def kick(self, ctx, user : discord.User, *, reason : str = ''):
        ''' Kicks the user mentioned with reason
            If server has log channel it is logged
        '''

        try:
            if reason == '':
                await ctx.guild.kick(user)
                await ctx.send("Done. User kicked")
            else:
                reason = self.cleanReason(reason)
                await ctx.guild.kick(user, reason=reason)
                await ctx.send(f"Done. User kicked for reason: `{reason}`")            
        
        except discord.errors.Forbidden:
            await ctx.send("Can't do that user has higher role than me")
        
        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

        else:
            if str(ctx.guild.id) in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                em = discord.Embed(type='rich', description=f'{ctx.author.mention} has kicked {user.mention} (ID: {user.id})')
                em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                if reason != '':
                    em.add_field(name='Reason:', value=f'```{reason}```')
                await log_channel.send(embed=em)

    @commands.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def ban(self, ctx, user : discord.User, reason : str = "", days : int = 0):
        ''' Bans the user mentioned with reason, number of days to delete message comes after
            If server has log channel it is logged
        '''

        try:
            if reason == '':
                await ctx.guild.ban(user, delete_message_days=days)
                await ctx.send("Done. User banned")
            else:
                reason = self.cleanReason(reason)
                await ctx.guild.ban(user, reason=reason, delete_message_days=days)
                await ctx.send(f"Done. User banned for reason: `{reason}`")

        except discord.errors.Forbidden:
            await ctx.send("Can't do that user has higher role than me")
        
        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

        else:
            if str(ctx.guild.id) in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                em = discord.Embed(type='rich', description=f'{ctx.author.mention} has banned {user.mention} (ID: {user.id})')
                em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                if reason != '':
                    em.add_field(name='Reason:', value=f'```{reason}```')
                await log_channel.send(embed=em)

    @commands.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def unban(self, ctx, uid : int, *, reason : str = ''):
        ''' Unbans the id given with the reason if it is given
        '''
        
        bans = await ctx.guild.bans()
        user = None

        if bans:
            for ban in bans:
                if ban.user.id == uid:
                    user = ban.user
                    break

        if user is not None:      
            try:
                if reason == '':
                    await ctx.guild.unban(user)
                    await ctx.send("Done. User unbanned")
                else:
                    reason = self.cleanReason(reason)
                    await ctx.guild.unban(user, reason=reason)
                    await ctx.send(f"Done. User unbanned for reason: `{reason}`")

            except discord.errors.Forbidden:
                await ctx.send("I lack the permissions to unban")

            except discord.errors.HTTPException:
                await ctx.send("Something went wrong. Please try again")

            else:
                if str(ctx.guild.id) in self.logging_channels:
                    log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                    em = discord.Embed(type='rich', description=f'{ctx.author.mention} has unbanned {user.name}')
                    em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                    if reason != '':
                        em.add_field(name='Reason:', value=f'```{reason}```')
                    await log_channel.send(embed=em)
        else:
            ctx.send(f'I can not find the banned user with ID: {uid}')


    @commands.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def softban(self, ctx, user : discord.Member, *, reason : str = ""):
        ''' Softbans the user mentioned with reason. Uses as a kick that cleans up mesages
            If server has a log channel it is logged
        '''

        try:
            if reason == '':
                await ctx.guild.ban(user, delete_message_days=1)
                await ctx.guild.unban(user)
                await ctx.send("Done. User softbanned")
            else:
                reason = self.cleanReason(reason)
                await ctx.guild.ban(user, reason=f'Softban: {reason}', delete_message_days=1)
                await ctx.guild.unban(user, reason=reason)
                await ctx.send(f"Done. User softbanned for reason: `{reason}`")

        except discord.errors.Forbidden:
            await ctx.send("Can't do that user has higher role than me")
        
        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

        else:
            if str(ctx.guild.id) in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                em = discord.Embed(type='rich', description=f'{ctx.author.mention} has softbanned {user.mention} (ID: {user.id})')
                em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                if reason != '':
                    em.add_field(name='Reason:', value=f'```{reason}```')
                await log_channel.send(embed=em)

    @commands.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def rename(self, ctx, user : discord.Member, *, nickname : str = ''):
        ''' Renames the mentioned user. No nickname given removes it
        '''

        old_name = user.display_name
        
        if nickname == '':
            nickname = None
        else:
            nickname = nickname.strip()

        try:
            await user.edit(nick=nickname)
            await ctx.send("Users Nickname has been changed")

        except discord.errors.Forbidden:
            await ctx.send("I can't do that. I lack the permissions to do so")
        
        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")
        
        else:
            if str(ctx.guild.id) in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                em = discord.Embed(type='rich', description=f'{ctx.author.mention} has renamed {old_name} to {user.display_name}')
                em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                await log_channel.send(embed=em)

    @commands.group()
    @commands.guild_only()
    @permissions.checkMod()
    async def cleanup(self, ctx):
        ''' Deletes messages

            cleanup messages [number] - removes number amount of messages
            cleanup user [name/mention] [number] - remove number amount of users messages
            cleanup text "Text" [number] - removes number amount of messages with text in it
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @cleanup.after_invoke
    async def after_cleanup_command(self, ctx):
        ''' Delete the cleanup command message after it is done
        '''
        if ctx.invoked_subcommand:
            await ctx.message.delete()

    @cleanup.command()
    @commands.guild_only()
    async def text(self, ctx, text : str, number : int = 1):
        ''' Deletes the last X messages containing the text specified
            Double quotes are needed for the text string

            Example: cleanup text "Test" 5
        '''

        message = ctx.message
        deleted = 0

        try:
            while number > 0:
                async for log_message in ctx.channel.history(limit=10, before=message):
                    if text.lower() in log_message.content.lower():
                        await log_message.delete(reason=f'Cleanup text: {text} by {ctx.author.name}')
                        await asyncio.sleep(0.25)
                        number -= 1
                        message = log_message
                        deleted += 1
                    if number == 0:
                        break

            # Log in the clean up in log_channel if set up
            if str(ctx.guild.id) in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                em = discord.Embed(type='rich', description=f'{ctx.author.mention} has cleaned up **{deleted}** messages containing **{text}** in {ctx.channel.mention}')
                em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                await log_channel.send(embed=em)

        except discord.errors.Forbidden:
            await ctx.send("I can't do that. I lack the permissions to do so")

        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

    @cleanup.command()
    @commands.guild_only()
    async def user(self, ctx, user : discord.Member, number : int = 1):
        ''' Deletes the last X messages from specified user
            
            Example:
            cleanup user @name 2
            cleanup user name 2
        '''

        message = ctx.message
        deleted = 0

        try:
            while number > 0:
                async for log_message in ctx.channel.history(limit=10, before=message):
                    if log_message.author.id == user.id:
                        await log_message.delete(reason=f'Cleanup user: {user.display_name} by {ctx.author.name}')
                        await asyncio.sleep(0.25)
                        number -= 1
                        message = log_message
                        deleted += 1
                    if number == 0:
                        break

            # Log in the clean up in log_channel if set up
            if str(ctx.guild.id) in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                em = discord.Embed(type='rich', description=f'{ctx.author.mention} has cleaned up **{deleted}** messages by **{user.display_name}** in {ctx.channel.mention}')
                em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                await log_channel.send(embed=em)

        except discord.errors.Forbidden:
            await ctx.send("I can't do that. I lack the permissions to do so")

        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

    @cleanup.command()
    @commands.guild_only()
    async def messages(self, ctx, number : int = 2):
        ''' Deletes the last X messages from specified user
            
            Example: cleanup messages 2
        '''

        if number < 2 or number > 100:
            await ctx.send('This command has to delete between 2 and 100 messages')
        else:
            to_delete = []

            # Get the messages to delete (amount = number)
            async for log_message in ctx.channel.history(limit=number, before=ctx.message):
                to_delete.append(log_message)
            
            try:
                await ctx.channel.delete_messages(to_delete, reason=f'Cleanup messages by {ctx.author.name}')

            except discord.errors.Forbidden:
                await ctx.send("I can't do that. I lack the permissions to do so")

            except discord.errors.HTTPException:
                await ctx.send("Something went wrong. Please try again")

            else:
                # Log in the clean up in log_channel if set up
                if str(ctx.guild.id) in self.logging_channels:
                    log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                    em = discord.Embed(type='rich', description=f'{ctx.author.mention} has cleaned up **{number}** messages in {ctx.channel.mention}')
                    em.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                    await log_channel.send(embed=em)

    @commands.group(name='filter')
    @commands.guild_only()
    async def _filter(self, ctx):
        ''' Adds or removes words from the filter
            It ignores case and will also remove the word if it is contained in another
            It can also remove full sentences if needed
        '''
        
        if ctx.invoked_subcommand is None:
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @_filter.group(name='server')
    @commands.guild_only()
    async def filter_server(self, ctx):
        ''' Adds or removes words from the server wide filter
            It ignores case and will also remove the word if it is contained in another
            It can also remove full sentences if needed
        '''
        
        if ctx.subcommand_passed == 'server':
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @filter_server.command(name='show')
    @commands.guild_only()
    async def filter_server_show(self, ctx):
        ''' Shows the current filtered words and sentences for the server
            Shows each on a single line will also send mutiple messages if needed
        '''

        # Check if the server has words being filtered at all
        if str(ctx.guild.id) in self.filter:
            if self.filter[str(ctx.guild.id)]['server']:
                msg = f'Server Wide Filter for {ctx.guild.name}:\n```\n'
                for filtered in self.filter[str(ctx.guild.id)]['server']:
                    msg += '"{0}" '.format(filtered)
                    # If the length of the messages is greater than 1600 send it and make another message for the rest
                    if len(msg) > 1600:
                        msg += '\n```'
                        await ctx.author.send(msg)
                        msg = '```\n'
                # Send message
                msg += '\n```'
                await ctx.author.send(msg)
                await ctx.send('List sent in DM')
            else:
                await ctx.send('Nothing is being filtered server wide')
        else:
            await ctx.send('Nothing is being filtered in this server at all')

    @filter_server.command(name='add')
    @commands.guild_only()
    @permissions.checkAdmin()
    async def filter_server_add(self, ctx, *words : str):
        ''' Adds words or sentences to the server wide filter.
            Make sure to use double quotes for sentences
            Examples:
            filter server add word1 word2 word3
            filter server add "This is a sentence"
        '''

        words_added = False # Used just to know if the file is to be saved
        
        # Check if any words were suppiled
        if words:            
            # Check if bot can even delete messages as there is no point in adding to filter if it can't
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                # Check if server has a dict in the filter file if not make one
                if str(ctx.guild.id) not in self.filter:
                    self.filter[str(ctx.guild.id)] = {'message': None, 'server': [], 'channels': {}}
                    self.bot.logger.info(f'Server {ctx.guild.name} ({ctx.guild.id}) has been added to the filter')
                
                # Loop over each word in words
                for word in words:
                    # Check if word is already being filtered if it is just ignore it
                    if word.lower() in self.filter[str(ctx.guild.id)]['server']:
                        continue
                    else:
                        self.filter[str(ctx.guild.id)]['server'].append(word.lower())
                        words_added = True
                
                # Save the file if needed
                if words_added:
                    self.bot.logger.info(f'{ctx.guild.name} ({ctx.guild.id}) has added words to filter')
                    utils.saveCogConfig(self, 'filter.json', self.filter)

                # Send message saying words have been added
                await ctx.send(f'{ctx.author.mention}, Words have been added to the server wide filter')
            else:
                await ctx.send(f'{ctx.author.mention}, I don\'t have the permissions to delete messages so I can\'t filter anything')
        else:
            await ctx.send(f'{ctx.author.mention}, You need to give me something to filter')

    @filter_server.command(name='remove')
    @commands.guild_only()
    @permissions.checkAdmin()
    async def filter_server_remove(self, ctx, *words : str):
        ''' Removes words or sentences from the server wide filter
            Make sure to use double quotes for sentences
            Examples:
            filter remove word1 word2 word3
            filter remove "This is a sentence"
        '''

        words_removed = False # Used just to know if the file is to be saved
        
        # Check if any words were suppiled
        if words:
            # Check if server has a dict in the filter file
            if str(ctx.guild.id) in self.filter:
                # Check if anything is being filtered server wide
                if self.filter[str(ctx.guild.id)]['server']:
                    # Loop over words
                    for word in words:
                        if word.lower() not in self.filter[str(ctx.guild.id)]['server']:
                            continue
                        else:
                            self.filter[str(ctx.guild.id)]['server'].remove(word.lower())
                            words_removed = True
                    
                    # Check if the filter for that server is empty if so remove it
                    if len(self.filter[str(ctx.guild.id)]['server']) == 0 and len(self.filter[str(ctx.guild.id)]['channels']) == 0:
                        self.filter.pop(str(ctx.guild.id))
                        self.bot.logger.info(f'Server {ctx.guild.name} ({ctx.guild.id}) has been removed from the filter')
                    
                    # Save the file is needed
                    if words_removed:
                        self.bot.logger.info(f'{ctx.guild.name} ({ctx.guild.id}) has removed words from filter')
                        utils.saveCogConfig(self, 'filter.json', self.filter)
                    
                    # Send message saying words have been added
                    await ctx.send(f'{ctx.author.mention}, Words have been removed from the filter')
                else:
                    await ctx.send(f'{ctx.author.mention}, Nothing is being filtered server wide')
            else:
                await ctx.send(f'{ctx.author.mention}, Nothing is being filtered in this server at all')
        else:
            await ctx.send(f'{ctx.author.mention}, You need to give me words to remove from the filter')

    @_filter.group(name='channel')
    @commands.guild_only()    
    async def filter_channel(self, ctx):
        ''' Adds or removes words from the current channel filter
            It ignores case and will also remove the word if it is contained in another
            It can also remove full sentences if needed
        '''
        
        if ctx.subcommand_passed == 'channel':
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @filter_channel.command(name='show')
    @commands.guild_only()  
    async def filter_channel_show(self, ctx):
        ''' Shows the current filtered words and sentences for the current channel
            Shows each on a single line will also send mutiple messages if needed
        '''

        # Check if the server has words being filtered at all
        if str(ctx.guild.id) in self.filter:
            if str(ctx.channel.id) in self.filter[str(ctx.guild.id)]['channels']:
                msg = f'Channel Only Filter for {ctx.channel.name}:\n```\n'
                for filtered in self.filter[str(ctx.guild.id)]['channels'][str(ctx.channel.id)]:
                    msg += '"{0}" '.format(filtered)
                    # If the length of the messages is greater than 1600 send it and make another message for the rest
                    if len(msg) > 1600:
                        msg += '\n```'
                        await ctx.author.send(msg)
                        msg = '```\n'
                # Send message
                msg += '\n```'
                await ctx.author.send(msg)
                await ctx.send('List sent in DM')
            else:
                await ctx.send('Nothing is being filtered in this channel (except server wide filter)')
        else:
            await ctx.send('Nothing is being filtered in this server at all')

    @filter_channel.command(name='add')
    @commands.guild_only()  
    @permissions.checkMod()
    async def filter_channel_add(self, ctx, *words : str):
        ''' Adds words or sentences to the current channel filter.
            Make sure to use double quotes for sentences
            Examples:
            filter server add word1 word2 word3
            filter server add "This is a sentence"
        '''

        words_added = False # Used just to know if the file is to be saved
        
        # Check if any words were suppiled
        if words:
            # Check if bot can even delete messages as there is no point in adding to filter if it can't
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                # Check if server has a dict in the filter file if not make one
                if str(ctx.guild.id) not in self.filter:
                    self.filter[str(ctx.guild.id)] = {'message': None, 'server': [], 'channels': {}}
                    self.bot.logger.info(f'Server {ctx.guild.name} ({ctx.guild.id}) has been added to the filter')
                
                # Check that the channel has a filter list if not make one
                if str(ctx.channel.id) not in self.filter[str(ctx.guild.id)]['channels']:
                    self.filter[str(ctx.guild.id)]['channels'][str(ctx.channel.id)] = []
                
                # Loop over each word in words
                for word in words:
                    # Check if word is already being filtered if it is just ignore it
                    if word.lower() in self.filter[str(ctx.guild.id)]['channels'][str(ctx.channel.id)]:
                        continue
                    else:
                        self.filter[str(ctx.guild.id)]['channels'][str(ctx.channel.id)].append(word.lower())
                        words_added = True
                
                # Save the file if needed
                if words_added:
                    self.bot.logger.info(f'{ctx.guild.name} ({ctx.guild.id}) has added words to filter')
                    utils.saveCogConfig(self, 'filter.json', self.filter)
                
                # Send message saying words have been added
                await ctx.send(f'{ctx.author.mention}, Words have been added to the current channels filter')
            else:
                await ctx.send(f'{ctx.author.mention}, I don\'t have the permissions to delete messages so I can\'t filter anything')
        else:
            await ctx.send(f'{ctx.author.mention}, You need to give me something to filter')

    @filter_channel.command(name='remove')
    @commands.guild_only()
    @permissions.checkMod()
    async def filter_channel_remove(self, ctx, *words : str):
        ''' Removes words or sentences from the current channel filter
            Make sure to use double quotes for sentences
            Examples:
            filter remove word1 word2 word3
            filter remove "This is a sentence"
        '''

        words_removed = False # Used just to know if the file is to be saved
        
        # Check if any words were suppiled
        if words:
            # Check if server has a dict in the filter file
            if str(ctx.guild.id) in self.filter:
                # Check if anything is being filtered in the channel
                if str(ctx.channel.id) in self.filter[str(ctx.guild.id)]['channels']:
                    # Loop over words
                    for word in words:
                        if word.lower() not in self.filter[str(ctx.guild.id)]['channels'][str(ctx.channel.id)]:
                            continue
                        else:
                            self.filter[str(ctx.guild.id)]['channels'][str(ctx.channel.id)].remove(word.lower())
                            words_removed = True
                    
                    # Check if current channel filter is empty if it is remove it
                    if len(self.filter[str(ctx.guild.id)]['channels'][str(ctx.channel.id)]) == 0:
                        self.filter[str(ctx.guild.id)]['channels'].pop(str(ctx.channel.id))
                    
                    # Check if the filter for that server is empty if so remove it
                    if len(self.filter[str(ctx.guild.id)]['server']) == 0 and len(self.filter[str(ctx.guild.id)]['channels']) == 0:
                        self.filter.pop(str(ctx.guild.id))
                        self.bot.logger.info(f'Server {ctx.guild.name} ({ctx.guild.id}) has been removed from the filter')

                    # Save the file is needed
                    if words_removed:
                        self.bot.logger.info(f'{ctx.guild.name} ({ctx.guild.id}) has removed words from filter')
                        utils.saveCogConfig(self, 'filter.json', self.filter)

                    # Send message saying words have been added
                    await ctx.send(f'{ctx.author.mention}, Words have been removed from the current channels filter')
                else:
                    await ctx.send(f'{ctx.author.mention}, Nothing is being filtered in this channel (except server wide filter)')
            else:
                await ctx.send(f'{ctx.author.mention}, Nothing is being filtered in this server at all')
        else:
            await ctx.send(f'{ctx.author.mention}, You need to give me words to remove from the filter')

    @_filter.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def message(self, ctx, *, msg : str = ''):
        ''' Makes the bot send a message when something is filtered
            No args removes the message
            Using %user% in the message will make the bot place a mention to the user whose messages was filtered
        '''

        # Check if anything is being filtered for that server
        if str(ctx.guild.id) in self.filter:
            # Check is message is empty
            if msg == '':
                self.filter[str(ctx.guild.id)]['message'] = None
                await ctx.send(f'{ctx.author.mention}, Filter messages has been removed')
            else:
                self.filter[str(ctx.guild.id)]['message'] = msg
                await ctx.send(f'{ctx.author.mention}, Filter messages has been set to: `{msg}`')
            
            # Save the filter file
            self.bot.logger.info(f'{ctx.guild.name} ({ctx.guild.id}) has changed the filter message')
            utils.saveCogConfig(self, 'filter.json', self.filter)

        else:
            await ctx.send(f'{ctx.author.mention}, Nothing is being filtered so there is no point in setting a message right now')

    def filter_immune(self, message):
        ''' Check if user can not be filtered
        '''

        # Check if bot owner
        if message.author.id in self.bot.config['ownerid']:
            return True
        elif message.channel.permissions_for(message.author).manage_messages:
            # Admin in server
            return True
        elif message.channel.permissions_for(message.author).manage_channels:
            # Mod in server
            return True

    async def check_filter(self, message):
        ''' Check if the message contains a filtered word from a server
        '''

        # Check that the message was not a DM
        if isinstance(message.channel, discord.abc.GuildChannel):
            # Double check bot can delete messages in server
            if message.channel.permissions_for(message.guild.me).manage_messages:
                # Check the sever has words in filter
                if str(message.guild.id) in self.filter:
                    # Check user is not immune from filter
                    if not self.filter_immune(message):
                        # Check server wide filter first
                        for word in self.filter[str(message.guild.id)]['server']:
                            reg = ''
                            for letter in word:
                                reg += '{0}+[{1}]*'.format(letter, asciipunct)
                            found = re.search(reg, message.content.replace('\\', ''), re.IGNORECASE)
                            # If re found the word delete it and tell the user
                            if found is not None:
                                await message.delete()
                                if self.filter[str(message.guild.id)]['message'] is not None:
                                    await message.channel.send(self.filter[str(message.guild.id)]['message'].replace('%user%' , message.author.mention))
                                break
                        else:
                            # Check if channel is in filter if server wide did not trigger
                            if str(message.channel.id) in self.filter[str(message.guild.id)]['channels']:
                                for word in self.filter[str(message.guild.id)]['channels'][str(message.channel.id)]:
                                    reg = ''
                                    for letter in word:
                                        reg += '{0}+[{1}]*'.format(letter, asciipunct)
                                    found = re.search(reg, message.content.replace('\\', ''), re.IGNORECASE)
                                    # If re found the word delete it and tell the user
                                    if found is not None:
                                        await message.delete()
                                        if self.filter[str(message.guild.id)]['message'] is not None:
                                            await message.channel.send(self.filter[str(message.guild.id)]['message'].replace('%user%' , message.author.mention))
                                        break

    async def check_edit_filter(self, before, after):
        ''' Check if the edited message contains a filtered word from a server
        '''

        message = after
        # Check that the message was not a DM
        if isinstance(message.channel, discord.abc.GuildChannel):
            # Double check bot can delete messages in server
            if message.channel.permissions_for(message.guild.me).manage_messages:
                # Check the sever has words in filter
                if str(message.guild.id) in self.filter:
                    # Check user is not immune from filter
                    if not self.filter_immune(message):
                        # Check server wide filter first
                        for word in self.filter[str(message.guild.id)]['server']:
                            reg = ''
                            for letter in word:
                                reg += '{0}+[{1}]*'.format(letter, asciipunct)
                            found = re.search(reg, message.content.replace('\\', ''), re.IGNORECASE)
                            # If re found the word delete it and tell the user
                            if found is not None:
                                await message.delete()
                                if self.filter[str(message.guild.id)]['message'] is not None:
                                    await message.channel.send(self.filter[str(message.guild.id)]['message'].replace('%user%' , message.author.mention))
                                break
                        else:
                            # Check if channel is in filter if server wide did not trigger
                            if str(message.channel.id) in self.filter[str(message.guild.id)]['channels']:
                                for word in self.filter[str(message.guild.id)]['channels'][str(message.channel.id)]:
                                    reg = ''
                                    for letter in word:
                                        reg += '{0}+[{1}]*'.format(letter, asciipunct)
                                    found = re.search(reg, message.content.replace('\\', ''), re.IGNORECASE)
                                    # If re found the word delete it and tell the user
                                    if found is not None:
                                        await message.delete()
                                        if self.filter[str(message.guild.id)]['message'] is not None:
                                            await message.channel.send(self.filter[str(message.guild.id)]['message'].replace('%user%' , message.author.mention))
                                        break

def setup(bot):
    n = mod(bot)
    bot.add_listener(n.check_filter, "on_message")
    bot.add_listener(n.check_edit_filter, "on_message_edit")
    bot.add_cog(n)