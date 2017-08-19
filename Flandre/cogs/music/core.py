''' Holds the music cog '''

import asyncio
import logging

import discord
from discord.ext import commands

from Flandre import utils, permissions

from . import utils as cogutils
from .player import MusicPlayer

logger = logging.getLogger(__package__)

class Music:
    '''
    Music player
    Create a server music player upon connect command which if music channel is forced
    '''

    def __init__(self, bot):
        self.bot = bot
        self.musicplayers = {}
        self.music_channels = cogutils.load_channels_file()

    def __unload(self):
        # Disconnect the bot from all active guilds
        # When reloading/unloading then delete the music player
        for guild, player in self.musicplayers.copy().items():
            asyncio.ensure_future(player.disconnect(self.bot.user, force=True, reloaded=True))
            self.bot.logger.info(f'Forcefully deleted {guild} music player')
            del self.musicplayers[guild]

    async def __local_check(self, ctx):
        return utils.check_enabled(ctx)

    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def setmusicchannel(self, ctx):
        '''Sets the channel command is typed in as the music channel for that guild '''

        removed = False
        # Check if the guild has set a music channel
        if str(ctx.guild.id) in self.music_channels:
            # Check if they are removing the channel or moving it
            if self.music_channels[str(ctx.guild.id)] != ctx.channel.id:
                self.music_channels[str(ctx.guild.id)] = ctx.channel.id

            else:
                self.music_channels.pop(str(ctx.guild.id))
                removed = True
        else:
            # IF they don't have one make the one the command is typed in the channel
            self.music_channels[str(ctx.guild.id)] = ctx.channel.id

        # Save the json file
        cogutils.save_channels_file(self.music_channels)

        # Tell the user the right message
        if removed:
            await ctx.send('This channel is no longer the music channel for the server.')
            log_msg = (f'Music channels has been saved. '
                       f'Reason: {ctx.channel.name} ({ctx.channel.id}) '
                       'is no longer a music channel')

            logger.info(log_msg)

        else:
            await ctx.send('This channel has been made the music channel for the server.')
            log_msg = (f'Music channels has been saved. '
                       f'Reason: {ctx.channel.name} ({ctx.channel.id}) '
                       'has been made a music channel')

            logger.info(log_msg)

    @commands.command()
    @commands.guild_only()
    async def connect(self, ctx):
        ''' Connects Bot to voice channel if not in one. Moves to channel if in already in one '''


        # Check if the have a music player
        if str(ctx.guild.id) not in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                # Create the music player for the guild and connect it
                self.musicplayers[str(ctx.guild.id)] = MusicPlayer(self.bot)
                logger.info(f'Created Music Player for {ctx.guild.name} ({ctx.guild.id})')
                await self.musicplayers[str(ctx.guild.id)].connect(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    # Create the music player for the guild and connect it
                    self.musicplayers[str(ctx.guild.id)] = MusicPlayer(self.bot)
                    log_msg = f'Created Music Player for {ctx.guild.name} ({ctx.guild.id})'
                    logger.info(log_msg)
                    await self.musicplayers[str(ctx.guild.id)].connect(ctx)

                else:
                    # Tell user that commands have to go in the force channel
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            # If they have a music player
            # Check if the channel is the forced music channel and tell the bot to connect/move
            if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                await self.musicplayers[str(ctx.guild.id)].connect(ctx)

            else:
                # Tell user that commands have to go in the force channel
                music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                await ctx.send(f'Music commands need to be done in {music_channel.mention}')

    @commands.command()
    @commands.guild_only()
    async def disconnect(self, ctx):
        ''' Disconnect the bot from the voice channel (mod only) '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                # Disconnect the bot and delete the player if successful
                done = await self.musicplayers[str(ctx.guild.id)].disconnect(ctx.author)
                if done:
                    del self.musicplayers[str(ctx.guild.id)]
                    log_msg = f'Removed Music Player for {ctx.guild.name} ({ctx.guild.id})'
                    logger.info(log_msg)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    # Disconnect the bot and delete the player if successful
                    done = await self.musicplayers[str(ctx.guild.id)].disconnect(ctx.author)
                    if done:
                        del self.musicplayers[str(ctx.guild.id)]
                        log_msg = f'Removed Music Player for {ctx.guild.name} ({ctx.guild.id})'
                        logger.info(log_msg)

                else:
                    # Tell user that commands have to go in the force channel
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    async def add(self, ctx, *, link: str):
        ''' Add command <Youtube Link/Soundcloud Link/Search term> '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                # Try to add the link as a song
                await self.musicplayers[str(ctx.guild.id)].add_queue(ctx, link)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    # Try to add the link as a song
                    await self.musicplayers[str(ctx.guild.id)].add_queue(ctx, link)

                else:
                    # Tell user that commands have to go in the force channel
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")
    
    @commands.command()
    @commands.guild_only()
    async def skip(self, ctx):
        ''' Vote skip '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].skip(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].skip(ctx)

                else:
                    # Tell user that commands have to go in the force channel
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")
    
    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def forceskip(self, ctx):
        ''' Force skip '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].skip(ctx, force=True)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].skip(ctx, force=True)

                else:
                    # Tell user that commands have to go in the force channel
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command(aliases=["vol"])
    @commands.guild_only()
    @permissions.check_mod()
    async def volume(self, ctx, percent: int):
        ''' Volume command <0 - 100 %> '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].change_volume(ctx, percent)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].change_volume(ctx, percent)

                else:
                    # Tell user that commands have to go in the force channel
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def pause(self, ctx):
        ''' Pause current song '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].pause_music(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].pause_music(ctx)

                else:
                    # Tell user that commands have to go in the force channe
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def resume(self, ctx):
        ''' Resume current song '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].resume_music(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].resume_music(ctx)

                else:
                    # Tell user that commands have to go in the force channe
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def clear(self, ctx):
        ''' Clear the queue '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].clear_queue(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].clear_queue(ctx)

                else:
                    # Tell user that commands have to go in the force channe
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    async def queue(self, ctx):
        ''' Show next few songs in the queue '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].show_queue(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].show_queue(ctx)

                else:
                    # Tell user that commands have to go in the force channe
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command(aliases=["np"])
    @commands.guild_only()
    async def nowplaying(self, ctx):
        ''' Show current playing song '''

        # Check if the have a music player
        if str(ctx.guild.id) in self.musicplayers:
            # Check if they are forcing a music channel
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].now_playing(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].now_playing(ctx)

                else:
                    # Tell user that commands have to go in the force channe
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')

        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    async def on_voice_state_update(self, member, before, after):
        ''' When voice channel update happens '''
        if before.channel is None:
            guild = after.channel.guild
        else:
            guild = before.channel.guild

        await asyncio.sleep(1)

        if str(guild.id) in self.musicplayers:
            voice = self.musicplayers[str(guild.id)]
            if voice.vc is None:
                if str(guild.id) in self.musicplayers:
                    del self.musicplayers[str(guild.id)]
                    logger.info(f'Removed Music Player for {guild.name} ({guild.id})')

            else:
                channelmembers = voice.channel.members

                # Do a check then wait 5 seconds if true
                if len(channelmembers) == 1:
                    await asyncio.sleep(5)

                    # Do check again
                    channelmembers = voice.channel.members
                    if len(channelmembers) == 1:
                        done = await self.musicplayers[str(guild.id)].disconnect(self.bot.user, force=True)

                        if done:
                            if str(guild.id) in self.musicplayers:
                                del self.musicplayers[str(guild.id)]
                            logger.info(f'Removed Music Player for {guild.name} ({guild.id})')
                else:
                    if str(guild.id) in self.musicplayers:
                        total_votes = len(voice.skips)
                        skips_needed = round(len(voice.channel.members) * 0.6)
                        # It the number of enough to pass skip
                        if total_votes >= skips_needed:
                            voice.skips.clear()
                            voice.vc.stop()
                            channel = voice.text_channel
                            await channel.send('A user has left the channel, and the skips needed now match'
                                               ' the current number of skips!! Skipping song')
