''' Holds the mod cog for the bot '''
import asyncio
import logging

import discord
from discord.ext import commands

from Flandre import utils, permissions

from . import logs

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

    async def member_ban(self, guild, user):
        ''' Event that is run on a member ban '''

        channel = self.bot.get_channel(self.logging_channels[str(guild.id)])
        await logs.ban_log_message(guild, user, channel)
    
    async def member_kick(self, member):
        '''
        Event that is run when a member leaves
        Used to check if someone was kicked
        '''

        guild = member.guild
        channel = self.bot.get_channel(self.logging_channels[str(guild.id)])
        await logs.kick_log_message(guild, member, channel)