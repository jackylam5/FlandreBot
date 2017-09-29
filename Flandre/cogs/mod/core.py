''' Holds the mod cog for the bot '''
import asyncio
import logging

import discord
from discord.ext import commands

from Flandre import utils, permissions

from . import logs, filter
from . import utils as cogutils

logger = logging.getLogger(__package__)

class Mod:
    ''' Moderation Tools '''

    def __init__(self, bot):
        self.bot = bot
        self.logging_channels = utils.load_cog_file('mod', 'logging_channels.json')
        self.message_channels = utils.load_cog_file('mod', 'message_channels.json')
        self.clean_up_messages = []
        self.filter = utils.load_cog_file('mod', 'filter.json')

    def __unload(self):
        ''' Remove listeners '''

        self.bot.remove_listener(self.member_ban, "on_member_ban")
        self.bot.remove_listener(self.member_kick, "on_member_remove")

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

        utils.save_cog_file('mod', 'logging_channels.json', self.logging_channels)

        if removed:
            await ctx.send('This channel is no longer the log channel for the mod actions.')
        else:
            await ctx.send('This channel has been made the log channel for the mod actions.')

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def kick(self, ctx, user: discord.User, *, reason: str = None):
        '''
        Kicks the user mentioned with reason
        If server has log channel it is logged
        '''

        try:
            if reason is None:
                await ctx.guild.kick(user)
                await ctx.send("Done. User kicked")
            else:
                reason = cogutils.clean_reason(self.bot, reason)
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
                embed = logs.create_log_embed('Kick Log', user, ctx.author, timestamp, reason)
                await log_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def ban(self, ctx, user: discord.User, *, reason: str = None):
        '''
        Bans the user mentioned with reason, will remove 1 day worth of messages
        If server has log channel it is logged
        '''

        try:
            if reason is None:
                await ctx.guild.ban(user, delete_message_days=1)
                await ctx.send("Done. User banned")
            else:
                reason = cogutils.clean_reason(self.bot, reason)
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
                timestamp = ctx.message.created_at
                embed = logs.create_log_embed('Ban Log', user, ctx.author, timestamp, reason)
                await log_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def softban(self, ctx, user: discord.Member, *, reason: str = None):
        '''
        Softbans the user mentioned with reason. Uses as a kick that cleans up mesages
        If server has a log channel it is logged
        '''

        try:
            if reason is None:
                await ctx.guild.ban(user, delete_message_days=1)
                await ctx.guild.unban(user)
                await ctx.send("Done. User softbanned")
            else:
                reason = cogutils.clean_reason(self.bot, reason)
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
                timestamp = ctx.message.created_at
                embed = logs.create_log_embed('Softban Log', user, ctx.author, timestamp, reason)
                await log_channel.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def unban(self, ctx, uid: int, *, reason: str = None):
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
                if reason is None:
                    await ctx.guild.unban(user)
                    await ctx.send("Done. User unbanned")
                else:
                    reason = cogutils.clean_reason(self.bot, reason)
                    await ctx.guild.unban(user, reason=reason)
                    await ctx.send(f"Done. User unbanned for reason: `{reason}`")

            except discord.errors.Forbidden:
                await ctx.send("I lack the permissions to unban")

            except discord.errors.HTTPException:
                await ctx.send("Something went wrong. Please try again")

            else:
                if str(ctx.guild.id) in self.logging_channels:
                    log_channel = self.bot.get_channel(self.logging_channels[str(ctx.guild.id)])
                    timestamp = ctx.message.created_at
                    embed = logs.create_log_embed('Unban Log', user, ctx.author, timestamp, reason)
                    await log_channel.send(embed=embed)
        else:
            ctx.send(f'I can not find the banned user with ID: {uid}')
    
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

        utils.save_cog_file('mod', 'message_channels.json', self.message_channels)

        if removed:
            await ctx.send('This channel is no longer the message channel for the cleanup actions.')
        else:
            await ctx.send('This channel has been made the message channel for the cleanup actions.')

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def cleanup(self, ctx, amount: int = 2):
        '''
        Deletes the amount of messages given in that channel
        Defaults to 2 if no argument is given
        '''

        if amount < 2 or amount > 100:
            await ctx.send('This command has to delete between 2 and 100 messages')
        else:
            to_delete = []

            # Get the messages to delete (amount = number)
            async for log_message in ctx.channel.history(limit=amount, before=ctx.message):
                to_delete.append(log_message)
                self.clean_up_messages.append(log_message.id)

            try:
                await ctx.channel.delete_messages(to_delete)

            except discord.errors.Forbidden:
                await ctx.send("I can't do that. I lack the permissions to do so")

            except discord.errors.HTTPException:
                await ctx.send("Something went wrong. Please try again")

            else:
                # Log in the clean up in log_channel if set up
                log_channel = None
                if str(ctx.guild.id) in self.message_channels:
                    log_channel = self.bot.get_channel(self.message_channels[str(ctx.guild.id)])

                    desc = (f'Channel: {ctx.channel.mention}\n'
                            f'Amount: {len(to_delete)}')
                    embed = discord.Embed(type='rich', description=desc)
                    embed.set_author(name='Cleanup Log')
                    embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url)
                    await log_channel.send(embed=embed)

    @cleanup.after_invoke
    async def after_cleanup_command(self, ctx):
        ''' Delete the cleanup command message after it is done '''
        if ctx.invoked_subcommand:
            self.clean_up_messages.append(ctx.message.id)
            await ctx.message.delete()

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

        if ctx.guild.id in self.filter:
            await filter.make_filter_list(ctx, self.filter)
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

        # Check if any words were suppiled
        if words:
            # Check if bot can even delete messages
            # As there is no point in adding to filter if it can't
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                self.filter = await filter.filter_add(ctx, self.filter, words)
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

        # Check if any words were suppiled
        if words:
            self.filter = await filter.filter_remove(ctx, self.filter, words)
        else:
            await ctx.send(f'{ctx.author.mention}, You haven\'t given anywords to be removed')

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

        if ctx.guild.id in self.filter:
            await filter.make_filter_list(ctx, self.filter, channel=True)
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

        # Check if any words were suppiled
        if words:
            # Check if bot can even delete messages
            # As there is no point in adding to filter if it can't
            if ctx.channel.permissions_for(ctx.me).manage_messages:
                self.filter = await filter.filter_add(ctx, self.filter, words, channel=True)
            else:
                msg = (f"{ctx.author.mention}, I don't have the permissions to delete messages "
                       "so I can't filter anything")
                await ctx.send(msg)
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

        # Check if any words were suppiled
        if words:
            self.filter = await filter.filter_remove(ctx, self.filter, words, channel=True)
        else:
            await ctx.send(f'{ctx.author.mention}, You haven\'t given anywords to be removed')

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
            logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                         'has changed the filter message'))

            utils.save_cog_file('mod', 'filter.json', self.filter)

        else:
            await ctx.send((f'{ctx.author.mention}, '
                            'Nothing is being filtered so there '
                            'is no point in setting a message right now'))

    async def member_ban(self, guild, user):
        ''' Event that is run on a member ban '''

        if str(guild.id) in self.logging_channels:
            channel = self.bot.get_channel(self.logging_channels[str(guild.id)])
            await logs.ban_log_message(guild, user, channel)

    async def member_kick(self, member):
        '''
        Event that is run when a member leaves
        Used to check if someone was kicked
        '''

        guild = member.guild
        if str(guild.id) in self.logging_channels:
            channel = self.bot.get_channel(self.logging_channels[str(guild.id)])
            await logs.kick_log_message(guild, member, channel)
