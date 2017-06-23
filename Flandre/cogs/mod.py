''' Hold the moderation cog for the mod '''
import asyncio
import logging
from io import StringIO, BytesIO
import re
from string import punctuation as asciipunct

import discord
from discord.ext import commands

from .. import permissions, utils

def clean_text(content):
    ''' Removes discord markdown '''
    content = content.replace('`', '')
    content = content.replace('*', '')
    content = content.replace('~', '')
    content = content.replace('_', '')
    content = content.replace('​', '')

    return content

class BanLogger:
    '''
    Used to make a logger for a banned users messages
    Then send it to the log channel
    '''

    def __init__(self, loop, user, channel):
        self.user = user
        self.channel = channel
        self.stream = StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s > %(message)s'))
        self.logger = logging.getLogger(self.user.name)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)
        self.log_task = loop.create_task(self.ban_log())

    async def ban_log(self):
        ''' Task to wait a bot then send a message to the channel '''

        # We will wait 10 seconds incase ban adding takes a while
        await asyncio.sleep(10)

        # Close logger
        self.handler.flush()
        self.stream.flush()
        self.logger.removeHandler(self.handler)
        self.logger = None

        logfile = BytesIO(bytes(self.stream.getvalue(), 'utf-8'))
        self.stream.close()
        desc = f'Name: {self.user.name}#{self.user.discriminator}'
        embed = discord.Embed(type='rich', description=desc)
        embed.set_author(name='Message Log (From Ban)')
        embed.set_thumbnail(url=self.user.avatar_url)
        await self.channel.send(embed=embed,
                                file=discord.File(logfile, filename=f"{self.user.name}_ban.log"))
        logfile.close()

class Mod:
    ''' Moderation tools '''

    def __init__(self, bot):
        self.bot = bot
        self.logging_channels = utils.check_cog_config(self, 'logging_channels.json')
        self.message_channels = utils.check_cog_config(self, 'message_channels.json')
        self.filter = utils.check_cog_config(self, 'filter.json')
        self.filtered_messages = []
        self.clean_up_messages = []
        self.ban_loggers = {}
        self.ban_log_check = self.bot.loop.create_task(self.ban_log_checker())

    def __unload(self):
        ''' Remove listeners '''

        self.bot.remove_listener(self.check_filter, "on_message")
        self.bot.remove_listener(self.check_edit_filter, "on_message_edit")
        self.bot.remove_listener(self.post_deleted_message, "on_message_delete")
        self.ban_loggers = {}
        self.ban_log_check.cancel()

    async def __local_check(self, ctx):
        return utils.check_enabled(ctx)

    async def ban_log_checker(self):
        ''' Removes empty ban loggers '''

        while True:
            if self.ban_loggers:
                for uid, logger in self.ban_loggers.copy().items():
                    if logger.logger is None:
                        del self.ban_loggers[uid]
                    else:
                        continue
            await asyncio.sleep(300)

    def clean_reason(self, reason):
        ''' Removes ` from the reason to stop escaping and format mentions if in reason '''

        reason = reason.replace('`', '')

        matches = re.findall('(<@!?(\d*)>)', reason)

        for match in matches:
            user = self.bot.get_user(int(match[1]))
            reason = reason.replace(match[0], f'@{user.name}#{user.discriminator}')

        return reason

    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def logchannel(self, ctx):
        ''' Sets the channel command is typed in as the log channel for that server '''
        removed = False
        if str(ctx.guild.id) in self.logging_channels:
            self.logging_channels.pop(str(ctx.guild.id))
            removed = True
        else:
            self.logging_channels[str(ctx.guild.id)] = ctx.channel.id

        utils.save_cog_config(self, 'logging_channels.json', self.logging_channels)

        if removed:
            await ctx.send('This channel is no longer the log channel for the mod actions.')
        else:
            await ctx.send('This channel has been made the log channel for the mod actions.')

    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def messagechannel(self, ctx):
        '''
        Sets the channel command is typed in as the message channel for that server
        Used to put message delete in this channel
        '''
        removed = False
        if str(ctx.guild.id) in self.message_channels:
            self.message_channels.pop(str(ctx.guild.id))
            removed = True
        else:
            self.message_channels[str(ctx.guild.id)] = ctx.channel.id

        utils.save_cog_config(self, 'message_channels.json', self.message_channels)

        if removed:
            await ctx.send('This channel is no longer the message channel for the cleanup actions.')
        else:
            await ctx.send('This channel has been made the message channel for the cleanup actions.')

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def kick(self, ctx, user: discord.User, *, reason: str = ''):
        '''
        Kicks the user mentioned with reason
        If server has log channel it is logged
        '''

        try:
            if reason == '':
                await ctx.guild.kick(user)
                await ctx.send("Done. User kicked")
            else:
                reason = self.clean_reason(reason)
                await ctx.guild.kick(user, reason=reason)
                await ctx.send(f"Done. User kicked for reason: `{reason}`")

        except discord.errors.Forbidden:
            await ctx.send("Can't do that user has higher role than me")

        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

        else:
            if str(ctx.guild.id) in self.logging_channels:
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                timestamp = ctx.message.created_at
                desc = f'Name: {user.name}\nID: {user.id}'
                embed = discord.Embed(type='rich', description=desc, timestamp=timestamp)
                embed.set_author(name='Kick Log')
                embed.set_thumbnail(url=user.avatar_url)
                embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url)
                if reason != '':
                    embed.add_field(name='Reason:', value=f'```{reason}```')
                await log_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def ban(self, ctx, user: discord.User, *, reason: str = ""):
        '''
        Bans the user mentioned with reason, will remove 1 day worth of messages
        If server has log channel it is logged
        '''

        try:
            if reason == '':
                await ctx.guild.ban(user, delete_message_days=1)
                await ctx.send("Done. User banned")
            else:
                reason = self.clean_reason(reason)
                await ctx.guild.ban(user, reason=reason, delete_message_days=1)
                await ctx.send(f"Done. User banned for reason: `{reason}`")

        except discord.errors.Forbidden:
            await ctx.send("Can't do that user has higher role than me")

        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

        else:
            if str(ctx.guild.id) in self.logging_channels:
                # Get log Channel
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])

                # Make the Ban message logger for the user
                if str(ctx.guild.id) in self.message_channels:
                    message_channel = self.bot.get_channel(self.message_channels[str(ctx.guild.id)])
                    self.ban_loggers[user.id] = BanLogger(self.bot.loop, user, message_channel)
                else:
                    self.ban_loggers[user.id] = BanLogger(self.bot.loop, user, log_channel)

                timestamp = ctx.message.created_at
                desc = f'Name: {user.name}\nID: {user.id}'
                embed = discord.Embed(type='rich', description=desc, timestamp=timestamp)
                embed.set_author(name='Ban Log')
                embed.set_thumbnail(url=user.avatar_url)
                embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url)
                if reason != '':
                    embed.add_field(name='Reason:', value=f'```{reason}```')
                await log_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def unban(self, ctx, uid: int, *, reason: str = ''):
        ''' Unbans the id given with the reason if it is given '''

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
                    reason = self.clean_reason(reason)
                    await ctx.guild.unban(user, reason=reason)
                    await ctx.send(f"Done. User unbanned for reason: `{reason}`")

            except discord.errors.Forbidden:
                await ctx.send("I lack the permissions to unban")

            except discord.errors.HTTPException:
                await ctx.send("Something went wrong. Please try again")

            else:
                if str(ctx.guild.id) in self.logging_channels:
                    log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                    desc = f'{ctx.author.mention} has unbanned {user.name}'
                    embed = discord.Embed(type='rich', description=desc)
                    time = ctx.message.created_at.strftime('%c')
                    embed.set_footer(text='Done at {0}'.format(time))
                    if reason != '':
                        embed.add_field(name='Reason:', value=f'```{reason}```')
                    await log_channel.send(embed=embed)
        else:
            ctx.send(f'I can not find the banned user with ID: {uid}')


    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def softban(self, ctx, user: discord.Member, *, reason: str = ""):
        '''
        Softbans the user mentioned with reason. Uses as a kick that cleans up mesages
        If server has a log channel it is logged
        '''

        try:
            if reason == '':
                await ctx.guild.ban(user, delete_message_days=1)
                await ctx.guild.unban(user)
                await ctx.send("Done. User softbanned")
            else:
                reason = self.clean_reason(reason)
                await ctx.guild.ban(user, reason=f'Softban: {reason}', delete_message_days=1)
                await ctx.guild.unban(user, reason=reason)
                await ctx.send(f"Done. User softbanned for reason: `{reason}`")

        except discord.errors.Forbidden:
            await ctx.send("Can't do that user has higher role than me")

        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

        else:
            if str(ctx.guild.id) in self.logging_channels:
                # Get log Channel
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])

                # Make the Ban message logger for the user
                if str(ctx.guild.id) in self.message_channels:
                    message_channel = self.bot.get_channel(self.message_channels[str(ctx.guild.id)])
                    self.ban_loggers[user.id] = BanLogger(self.bot.loop, user, message_channel)
                else:
                    self.ban_loggers[user.id] = BanLogger(self.bot.loop, user, log_channel)

                timestamp = ctx.message.created_at
                desc = f'Name: {user.name}\nID: {user.id}'
                embed = discord.Embed(type='rich', description=desc, timestamp=timestamp)
                embed.set_author(name='Softban Log')
                embed.set_thumbnail(url=user.avatar_url)
                embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url)
                if reason != '':
                    embed.add_field(name='Reason:', value=f'```{reason}```')
                await log_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def rename(self, ctx, user: discord.Member, *, nickname: str = ''):
        ''' Renames the mentioned user. No nickname given removes it '''

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
                desc = f'{ctx.author.mention} has renamed {old_name} to {user.display_name}'
                embed = discord.Embed(type='rich', description=desc)
                embed.set_footer(text='Done at {0}'.format(ctx.message.created_at.strftime('%c')))
                await log_channel.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @permissions.check_mod()
    async def cleanup(self, ctx):
        '''
        Deletes messages

        cleanup messages [number] - removes number amount of messages
        cleanup user [name/mention] [number] - remove number amount of users messages
        cleanup text "Text" [number] - removes number amount of messages with text in it
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @cleanup.after_invoke
    async def after_cleanup_command(self, ctx):
        ''' Delete the cleanup command message after it is done '''
        if ctx.invoked_subcommand:
            self.clean_up_messages.append(ctx.message.id)
            await ctx.message.delete()

    @cleanup.command()
    @commands.guild_only()
    async def text(self, ctx, text: str, number: int = 1):
        '''
        Deletes messages containing the text given within X messages

        Example: cleanup text "Test" 5
        '''

        def check(message):
            ''' Check if the text is in the message '''
            return text.lower() in message.content.lower()

        try:
            await ctx.channel.purge(limit=number, check=check)
            await ctx.send('Cleanup Done!')

            # Log in the clean up in log_channel if set up
            log_channel = None
            if str(ctx.guild.id) in self.message_channels:
                send_message = True
                log_channel = self.bot.get_channel(self.message_channels[str(ctx.guild.id)])
            elif str(ctx.guild.id) in self.logging_channels:
                send_message = True
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])

            if send_message:
                desc = (f'Channel: {ctx.channel.mention}\n'
                        f'Text: {text}\n')
                embed = discord.Embed(type='rich', description=desc)
                embed.set_author(name='Cleanup Log')
                embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url)
                await log_channel.send(embed=embed)

        except discord.errors.Forbidden:
            await ctx.send("I can't do that. I lack the permissions to do so")

        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

    @cleanup.command()
    @commands.guild_only()
    async def user(self, ctx, user: discord.Member, number: int = 1):
        '''
        Deletes all the messages from the user in the last X messages

        Example:
        cleanup user @name 2
        cleanup user name 2
        '''

        def check(message):
            ''' Check if the text is in the message '''
            return user is message.author

        try:
            await ctx.channel.purge(limit=number, check=check)
            await ctx.send('Cleanup Done!')

            # Log in the clean up in log_channel if set up
            send_message = False
            log_channel = None
            if str(ctx.guild.id) in self.message_channels:
                send_message = True
                log_channel = self.bot.get_channel(self.message_channels[str(ctx.guild.id)])
            elif str(ctx.guild.id) in self.logging_channels:
                send_message = True
                log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])

            if send_message:
                desc = (f'Channel: {ctx.channel.mention}\n'
                        f'From: {user.name}#{user.discriminator}\n')
                embed = discord.Embed(type='rich', description=desc)
                embed.set_author(name='Cleanup Log')
                embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url)
                await log_channel.send(embed=embed)

        except discord.errors.Forbidden:
            await ctx.send("I can't do that. I lack the permissions to do so")

        except discord.errors.HTTPException:
            await ctx.send("Something went wrong. Please try again")

    @cleanup.command()
    @commands.guild_only()
    async def messages(self, ctx, number: int = 2):
        '''
        Deletes the last X messages from specified user

        Example: cleanup messages 2
        '''

        if number < 2 or number > 100:
            await ctx.send('This command has to delete between 2 and 100 messages')
        else:
            to_delete = []

            # Get the messages to delete (amount = number)
            async for log_message in ctx.channel.history(limit=number, before=ctx.message):
                to_delete.append(log_message)
                self.clean_up_messages.append(log_message.id)

            try:
                reason = f'Cleanup messages by {ctx.author.name}'
                await ctx.channel.delete_messages(to_delete, reason=reason)

            except discord.errors.Forbidden:
                await ctx.send("I can't do that. I lack the permissions to do so")

            except discord.errors.HTTPException:
                await ctx.send("Something went wrong. Please try again")

            else:
                # Log in the clean up in log_channel if set up
                send_message = False
                log_channel = None
                if str(ctx.guild.id) in self.message_channels:
                    send_message = True
                    log_channel = self.bot.get_channel(self.message_channels[str(ctx.guild.id)])
                elif str(ctx.guild.id) in self.logging_channels:
                    send_message = True
                    log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])

                if send_message:
                    desc = (f'Channel: {ctx.channel.mention}\n'
                            f'Amount: {len(to_delete)}')
                    embed = discord.Embed(type='rich', description=desc)
                    embed.set_author(name='Cleanup Log')
                    embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url) 
                    await log_channel.send(embed=embed)

    @commands.group(name='filter')
    @commands.guild_only()
    async def _filter(self, ctx):
        '''
        Adds or removes words from the filter
        It ignores case and will also remove the word if it is contained in another
        It can also remove full sentences if needed
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @_filter.group(name='server')
    @commands.guild_only()
    async def filter_server(self, ctx):
        '''
        Adds or removes words from the server wide filter
        It ignores case and will also remove the word if it is contained in another
        It can also remove full sentences if needed
        '''

        if ctx.subcommand_passed == 'server':
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @filter_server.command(name='show')
    @commands.guild_only()
    async def filter_server_show(self, ctx):
        ''' Shows the current filtered words and sentences for the server
            Shows each on a single line will also send mutiple messages if needed
        '''

        guild_id = str(ctx.guild.id)
        # Check if the server has words being filtered at all
        if guild_id in self.filter:
            if self.filter[guild_id]['server']:
                msg = f'Server Wide Filter for {ctx.guild.name}:\n```\n'
                for filtered in self.filter[guild_id]['server']:
                    msg += '"{0}" '.format(filtered)
                    # If the length of the messages is greater than 1600
                    # Send it and make another message for the rest
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
    @permissions.check_admin()
    async def filter_server_add(self, ctx, *words: str):
        '''
        Adds words or sentences to the server wide filter.
        Make sure to use double quotes for sentences
        Examples:
        filter server add word1 word2 word3
        filter server add "This is a sentence"
        '''

        words_added = False # Used just to know if the file is to be saved
        guild_id = str(ctx.guild.id)

        # Check if any words were suppiled
        if words:
            # Check if bot can even delete messages
            # As there is no point in adding to filter if it can't
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                # Check if server has a dict in the filter file if not make one
                if guild_id not in self.filter:
                    self.filter[guild_id] = {'message': None, 'server': [], 'channels': {}}
                    self.bot.logger.info((f'Server {ctx.guild.name} ({ctx.guild.id}) '
                                          'has been added to the filter'))

                # Loop over each word in words
                for word in words:
                    word = word.lower()
                    # Check if word is already being filtered if it is just ignore it
                    if word in self.filter[guild_id]['server']:
                        continue
                    else:
                        self.filter[guild_id]['server'].append(word)
                        words_added = True

                # Save the file if needed
                if words_added:
                    self.bot.logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                                          'has added words to filter'))

                    utils.save_cog_config(self, 'filter.json', self.filter)

                # Send message saying words have been added
                await ctx.send((f'{ctx.author.mention}, '
                                'Words have been added to the server wide filter'))
            else:
                msg = (f"{ctx.author.mention}, I don't have the permissions to delete messages "
                       "so I can't filter anything")
                await ctx.send(msg)
        else:
            await ctx.send(f'{ctx.author.mention}, You need to give me something to filter')

    @filter_server.command(name='remove')
    @commands.guild_only()
    @permissions.check_admin()
    async def filter_server_remove(self, ctx, *words: str):
        '''
        Removes words or sentences from the server wide filter
        Make sure to use double quotes for sentences
        Examples:
        filter remove word1 word2 word3
        filter remove "This is a sentence"
        '''

        words_removed = False # Used just to know if the file is to be saved
        guild_id = str(ctx.guild.id)

        # Check if any words were suppiled
        if words:
            # Check if server has a dict in the filter file
            if guild_id in self.filter:
                # Check if anything is being filtered server wide
                if self.filter[guild_id]['server']:
                    # Loop over words
                    for word in words:
                        word = word.lower()
                        if word not in self.filter[guild_id]['server']:
                            continue
                        else:
                            self.filter[guild_id]['server'].remove(word)
                            words_removed = True

                    # Check if the filter for that server is empty if so remove it
                    server_len = len(self.filter[guild_id]['server'])
                    channel_len = len(self.filter[guild_id]['channels'])
                    if server_len == 0 and channel_len == 0:
                        self.filter.pop(guild_id)
                        self.bot.logger.info((f'Server {ctx.guild.name} ({ctx.guild.id}) '
                                              'has been removed from the filter'))

                    # Save the file is needed
                    if words_removed:
                        self.bot.logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                                              'has removed words from filter'))

                        utils.save_cog_config(self, 'filter.json', self.filter)

                    # Send message saying words have been added
                    await ctx.send(f'{ctx.author.mention}, Words have been removed from the filter')
                else:
                    await ctx.send(f'{ctx.author.mention}, Nothing is being filtered server wide')
            else:
                await ctx.send((f'{ctx.author.mention}, '
                                'Nothing is being filtered in this server at all'))
        else:
            await ctx.send((f'{ctx.author.mention}, '
                            'You need to give me words to remove from the filter'))

    @_filter.group(name='channel')
    @commands.guild_only()
    async def filter_channel(self, ctx):
        '''
        Adds or removes words from the current channel filter
        It ignores case and will also remove the word if it is contained in another
        It can also remove full sentences if needed
        '''

        if ctx.subcommand_passed == 'channel':
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @filter_channel.command(name='show')
    @commands.guild_only()
    async def filter_channel_show(self, ctx):
        '''
        Shows the current filtered words and sentences for the current channel
        Shows each on a single line will also send mutiple messages if needed
        '''

        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)

        # Check if the server has words being filtered at all
        if guild_id in self.filter:
            if channel_id in self.filter[guild_id]['channels']:
                msg = f'Channel Only Filter for {ctx.channel.name}:\n```\n'
                for filtered in self.filter[guild_id]['channels'][channel_id]:
                    msg += '"{0}" '.format(filtered)
                    # If the length of the messages is greater than 1600
                    # Send it and make another message for the rest
                    if len(msg) > 1600:
                        msg += '\n```'
                        await ctx.author.send(msg)
                        msg = '```\n'
                # Send message
                msg += '\n```'
                await ctx.author.send(msg)
                await ctx.send('List sent in DM')
            else:
                await ctx.send(('Nothing is being filtered in this channel '
                                '(except server wide filter)'))
        else:
            await ctx.send('Nothing is being filtered in this server at all')

    @filter_channel.command(name='add')
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_add(self, ctx, *words: str):
        '''
        Adds words or sentences to the current channel filter.
        Make sure to use double quotes for sentences
        Examples:
        filter server add word1 word2 word3
        filter server add "This is a sentence"
        '''

        words_added = False # Used just to know if the file is to be saved
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)

        # Check if any words were suppiled
        if words:
            # Check if bot can even delete messages
            # As there is no point in adding to filter if it can't
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                # Check if server has a dict in the filter file if not make one
                if guild_id not in self.filter:
                    self.filter[guild_id] = {'message': None, 'server': [], 'channels': {}}
                    self.bot.logger.info((f'Server {ctx.guild.name} ({ctx.guild.id}) '
                                          'has been added to the filter'))

                # Check that the channel has a filter list if not make one
                if channel_id not in self.filter[guild_id]['channels']:
                    self.filter[guild_id]['channels'][channel_id] = []

                # Loop over each word in words
                for word in words:
                    word = word.lower()
                    # Check if word is already being filtered if it is just ignore it
                    if word in self.filter[guild_id]['channels'][channel_id]:
                        continue
                    else:
                        self.filter[guild_id]['channels'][channel_id].append(word)
                        words_added = True

                # Save the file if needed
                if words_added:
                    self.bot.logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                                          'has added words to filter'))

                    utils.save_cog_config(self, 'filter.json', self.filter)

                # Send message saying words have been added
                await ctx.send((f'{ctx.author.mention}, '
                                'Words have been added to the current channels filter'))
            else:
                await ctx.send((f"{ctx.author.mention}, "
                                "I don't have the permissions to delete messages "
                                "so I can't filter anything"))
        else:
            await ctx.send(f'{ctx.author.mention}, You need to give me something to filter')

    @filter_channel.command(name='remove')
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_remove(self, ctx, *words: str):
        '''
        Removes words or sentences from the current channel filter
        Make sure to use double quotes for sentences
        Examples:
        filter remove word1 word2 word3
        filter remove "This is a sentence"
        '''

        words_removed = False # Used just to know if the file is to be saved
        guild_id = str(ctx.guild.id)
        channel_id = str(ctx.channel.id)

        # Check if any words were suppiled
        if words:
            # Check if server has a dict in the filter file
            if guild_id in self.filter:
                # Check if anything is being filtered in the channel
                if channel_id in self.filter[guild_id]['channels']:
                    # Loop over words
                    for word in words:
                        word = word.lower()
                        if word not in self.filter[guild_id]['channels'][channel_id]:
                            continue
                        else:
                            self.filter[guild_id]['channels'][channel_id].remove(word)
                            words_removed = True

                    # Check if current channel filter is empty if it is remove it
                    if self.filter[guild_id]['channels'][channel_id]:
                        self.filter[guild_id]['channels'].pop(channel_id)

                    # Check if the filter for that server is empty if so remove it
                    server_len = len(self.filter[guild_id]['server'])
                    channel_len = len(self.filter[guild_id]['channels'])
                    if server_len == 0 and channel_len == 0:
                        self.filter.pop(str(ctx.guild.id))
                        self.bot.logger.info((f'Server {ctx.guild.name} ({ctx.guild.id}) '
                                              'has been removed from the filter'))

                    # Save the file is needed
                    if words_removed:
                        self.bot.logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                                              'has removed words from filter'))

                        utils.save_cog_config(self, 'filter.json', self.filter)

                    # Send message saying words have been added
                    await ctx.send((f'{ctx.author.mention}, '
                                    'Words have been removed from the current channels filter'))
                else:
                    await ctx.send((f'{ctx.author.mention}, '
                                    'Nothing is being filtered in this channel '
                                    '(except server wide filter)'))
            else:
                await ctx.send((f'{ctx.author.mention}, '
                                'Nothing is being filtered in this server at all'))
        else:
            await ctx.send((f'{ctx.author.mention}, '
                            'You need to give me words to remove from the filter'))

    @_filter.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def message(self, ctx, *, msg: str = ''):
        '''
        Makes the bot send a message when something is filtered
        No args removes the message
        Using %user% in the message will make the bot place
        A mention to the user whose messages was filtered
        '''

        guild_id = str(ctx.guild.id)

        # Check if anything is being filtered for that server
        if guild_id in self.filter:
            # Check is message is empty
            if msg == '':
                self.filter[guild_id]['message'] = None
                await ctx.send(f'{ctx.author.mention}, Filter messages has been removed')
            else:
                self.filter[guild_id]['message'] = msg
                await ctx.send(f'{ctx.author.mention}, Filter messages has been set to: `{msg}`')

            # Save the filter file
            self.bot.logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                                  'has changed the filter message'))

            utils.save_cog_config(self, 'filter.json', self.filter)

        else:
            await ctx.send((f'{ctx.author.mention}, '
                            'Nothing is being filtered so there '
                            'is no point in setting a message right now'))

    def filter_immune(self, message):
        ''' Check if user can not be filtered '''

        if message.author.bot and message.author != self.bot.user:
            return False

        else:
            # Check if bot owner
            if message.author.id in self.bot.config['ownerid']:
                return True
            elif message.channel.permissions_for(message.author).manage_messages:
                # Admin in server
                return True
            elif message.channel.permissions_for(message.author).manage_channels:
                # Mod in server
                return True
            else:
                return False

    async def check_filter(self, message):
        ''' Check if the message contains a filtered word from a server '''

        # Check that the message was not a DM
        if isinstance(message.channel, discord.abc.GuildChannel):
            # Double check bot can delete messages in server
            if message.channel.permissions_for(message.guild.me).manage_messages:
                # Check the sever has words in filter
                if str(message.guild.id) in self.filter:
                    # Check user is not immune from filter
                    if not self.filter_immune(message):

                        # Filter out embed content
                        if message.embeds:
                            for embed in message.embeds:
                                embed_dict = embed.to_dict()
                                message.content += '{}\n'.format(embed_dict.get('description', ''))
                                message.content += '{}\n'.format(embed_dict.get('title', ''))

                                if 'fields' in embed_dict:
                                    for field in embed_dict['fields']:
                                        message.content += '{}\n'.format(field.get('name', ''))
                                        message.content += '{}\n'.format(field.get('value', ''))

                        guild_id = str(message.guild.id)
                        channel_id = str(message.channel.id)
                        author = message.author

                        # Check server wide filter first
                        for word in self.filter[guild_id]['server']:
                            cleaned_message = clean_text(message.content)
                            found = re.search(f'\\b{word}\\b', cleaned_message, re.IGNORECASE)
                            # If re found the word delete it and tell the user
                            if found is not None:
                                self.filtered_messages.append(message.id)
                                await message.delete()
                                msg = self.filter[guild_id]['message']
                                if msg is not None:
                                    msg = msg.replace('%user%', author.mention)
                                    await message.channel.send(msg)
                                break
                        else:
                            # Check if channel is in filter if server wide did not trigger
                            if channel_id in self.filter[guild_id]['channels']:
                                for word in self.filter[guild_id]['channels'][channel_id]:
                                    cleaned_message = clean_text(message.content)
                                    found = re.search(f'\\b{word}\\b', cleaned_message, re.IGNORECASE)
                                    # If re found the word delete it and tell the user
                                    if found is not None:
                                        self.filtered_messages.append(message.id)
                                        await message.delete()
                                        msg = self.filter[guild_id]['message']
                                        if msg is not None:
                                            msg = msg.replace('%user%', author.mention)
                                            await message.channel.send(msg)
                                        break

    async def check_edit_filter(self, before, after):
        ''' Check if the edited message contains a filtered word from a server '''

        # Check that the message was not a DM
        if isinstance(after.channel, discord.abc.GuildChannel):
            # Double check bot can delete messages in server
            if after.channel.permissions_for(after.guild.me).manage_messages:
                # Check the sever has words in filter
                if str(after.guild.id) in self.filter:
                    # Check user is not immune from filter
                    if not self.filter_immune(after):

                        # Filter out embed content
                        if after.embeds:
                            for embed in after.embeds:
                                embed_dict = embed
                                after.content += '{}\n'.format(embed_dict.get('description', ''))
                                after.content += '{}\n'.format(embed_dict.get('title', ''))

                                if 'fields' in embed_dict:
                                    for field in embed_dict['fields']:
                                        after.content += '{}\n'.format(field.get('name', ''))
                                        after.content += '{}\n'.format(field.get('value', ''))

                        guild_id = str(after.guild.id)
                        channel_id = str(after.channel.id)
                        author = after.author

                        # Check server wide filter first
                        for word in self.filter[guild_id]['server']:
                            cleaned_message = clean_text(after.content)
                            found = re.search(f'\\b{word}\\b', cleaned_message, re.IGNORECASE)
                            # If re found the word delete it and tell the user
                            if found is not None:
                                self.filtered_messages.append(after.id)
                                await after.delete()
                                msg = self.filter[guild_id]['message']
                                if msg is not None:
                                    await after.channel.send(msg.replace('%user%', author.mention))
                                break
                        else:
                            # Check if channel is in filter if server wide did not trigger
                            if channel_id in self.filter[guild_id]['channels']:
                                for word in self.filter[guild_id]['channels'][channel_id]:
                                    cleaned_message = clean_text(after.content)
                                    found = re.search(f'\\b{word}\\b', cleaned_message, re.IGNORECASE)
                                    # If re found the word delete it and tell the user
                                    if found is not None:
                                        self.filtered_messages.append(after.id)
                                        await after.delete()
                                        msg = self.filter[guild_id]['message']
                                        if msg is not None:
                                            msg = msg.replace('%user%', author.mention)
                                            await after.channel.send(msg)
                                        break

    async def post_deleted_message(self, message):
        ''' Post when a message is deleted to the log channel '''

        # We need to wait incase the ban log is made
        await asyncio.sleep(2)

        # Check message is not a DM
        if isinstance(message.channel, discord.abc.GuildChannel):
            if message.author != self.bot.user:

                if message.author.id not in self.ban_loggers:
                    # Log in the deleteion in log_channel if set up
                    send_message = False
                    log_channel = None
                    if str(message.guild.id) in self.message_channels:
                        send_message = True
                        log_channel = self.bot.get_channel(self.message_channels[str(message.guild.id)])
                    elif str(message.guild.id) in self.logging_channels:
                        send_message = True
                        log_channel = self.bot.get_channel(self.logging_channels[str(message.guild.id)])

                    if send_message:
                        desc = (f'Author: {message.author.name}#{message.author.discriminator}\n'
                                f'Channel: {message.channel.mention}\n'
                                f'Timestamp: {message.created_at.strftime("%c")}')

                        embed = discord.Embed(type='rich', description=desc)
                        embed.set_author(name='Message deletion')
                        embed.set_thumbnail(url=message.author.avatar_url)
                        if message.clean_content:
                            embed.add_field(name='Content:', value=message.clean_content)
                        if message.id in self.filtered_messages:
                            embed.set_footer(text='Done due to filter')
                            self.filtered_messages.remove(message.id)
                        elif message.id in self.clean_up_messages:
                            embed.set_footer(text='Done due to cleanup command')
                            self.clean_up_messages.remove(message.id)
                        else:
                            embed.set_footer(text='Done by user/staff')
                        await log_channel.send(embed=embed)
                else:
                    self.ban_loggers[message.author.id].logger.info(message.clean_content)

def setup(bot):
    ''' Setup for bot to add cog '''
    cog = Mod(bot)
    bot.add_listener(cog.check_filter, "on_message")
    bot.add_listener(cog.check_edit_filter, "on_message_edit")
    bot.add_listener(cog.post_deleted_message, "on_message_delete")
    bot.add_cog(cog)
