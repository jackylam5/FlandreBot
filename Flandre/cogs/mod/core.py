''' Holds the mod cog for the bot '''
import asyncio
import logging

import discord
from discord.ext import commands

from Flandre import utils, permissions

from . import logs
from . import utils as cogutils

logger = logging.getLogger(__package__)

class Mod:
    ''' Moderation Tools '''

    def __init__(self, bot):
        self.bot = bot
        self.logging_channels = utils.load_cog_file('mod', 'logging_channels.json')

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
