''' Holds the music cog for the bot '''
import asyncio
import functools
import time

import youtube_dl
import discord
from discord.ext import commands

from .. import permissions, utils


class Song:
    '''
    Song Class used to store song information in the queue so it can be easily accessed
    Takes the user that requested the song and the ytdl info of the song
    '''
    def __init__(self, requester, ytdl_info):
        self.requester = requester
        self.url = ytdl_info['webpage_url']
        self.download_url = ytdl_info['url']
        self.title = ytdl_info['title']
        self.duration = ytdl_info['duration']
        self.thumbnail = ytdl_info['thumbnail']


class MusicPlayer:
    '''
    Music Player Class
    Manages connecting and disconnecting of the bot to that guild
    Also manages adding and playing of songs for that guild
    '''

    def __init__(self, bot):
        self.bot = bot
        # The voice client for the guild
        self._vc = None
        # The channel the now playing messages get sent to
        self.text_channel = None
        # The current song being played and the queue and the voulume for the song and if any skips
        self.current = None
        self.queue = []
        self.volume = 0.1
        self.skips = set()
        # asyncio Events for if there are songs in queue and if the next song is to be played
        self.play_next_song = asyncio.Event()
        self.songs_in_queue = asyncio.Event()
        # Timestamp for when the song ends
        self.time_song_ends = None
        # Time left in seconds when the song is paused to get the new end timestamp
        self.paused_timeleft = None
        # Background task that plays the music for the server
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def check_mod(self, user):
        '''
        Check if user is mod needed as some admin commands can be used by non-admins
        If bot is not connected such as the first connect
        '''

        # Owner
        if user.id in self.bot.config['ownerid']:
            return True

        elif (self.text_channel.permissions_for(user).manage_guild or
              self.text_channel.permissions_for(user).manage_channels):
            # Mod +
            return True

        else:
            return False

    async def connect(self, ctx):
        '''
        Connects Bot to voice channel if not in one
        Move to channel if in already in one
        '''

        # Check the user is connected to voice
        if ctx.author.voice is None:
            await ctx.channel.send((f'{ctx.author.mention}, '
                                    'You need to be in a voice channel so I can connect to it'))

        else:
            # Check if there is a voice client for the server
            if self._vc is None:
                # Check if voice is still connected somehow
                for vc in self.bot.voice_clients:
                    if vc.guild == ctx.guild:
                        self._vc = vc
                        self.text_channel = ctx.channel

                        # Check if something is playing
                        if self._vc.is_playing or self._vc.is_paused:
                            self._vc.stop()

                        # Tell the user we have connected and bound messages to the channel
                        await ctx.send((f'Connected to **{self._vc.channel.name}** '
                                        'and bound to this text channel'))

                        break

                else:
                    # No voice client means bot is not connected so anyone can connect bot
                    # Connect to that voice channel
                    self._vc = await ctx.author.voice.channel.connect()
                    # Set text channel to the channel the message was sent in
                    self.text_channel = ctx.channel
                    # Tell the user we have connected and bound messages to the channel
                    await ctx.send((f'Connected to **{self._vc.channel.name}** '
                                    'and bound to this text channel'))

            else:
                # The bot is currently connected and needs to be move to a different channel
                # This can only be done by mods and above so we need to check that
                if self.check_mod(ctx.author):
                    # Check if the person asking the bot to move is not in the same channel
                    if ctx.author.voice.channel == self._vc.channel:
                        await ctx.send(f'{ctx.author.mention}, I am already in your voice channel')

                    else:
                        # Move to that channel
                        await self._vc.move_to(ctx.author.voice.channel)
                        # Set text channel to the channel the message was sent in
                        self.text_channel = ctx.channel
                        # Tell the user we have moved and bound messages to the channel
                        await ctx.send((f'Moved to **{self._vc.channel.name}** '
                                        'and bound to this text channel'))

                else:
                    # User is not mod or above so tell user they cannot move the bot
                    await ctx.send((f'Sorry {ctx.author.mention}, '
                                    'You need to be a mod or above to move me '
                                    'if I am already connected'))

    async def disconnect(self, user, force=False, reloaded=False):
        '''
        Disconnect the bot from the voice channel (mod only)
        If no one is in the voice channel the bot forces the disconnect using force
        If a cog reload happens force and reload are used to tell the users
        Using bot that a disconnect happened due to a reload
        This shouldn't happen unless the reload is really needed
        Return True if sucessful so the music player can be removed else return False
        '''

        # Check if the disconnect was forced or done by a mod+
        if force or self.check_mod(user):
            # Clear the queue
            self.queue = []

            # Check if the voice client is playing or paused and stop if it is
            if self._vc.is_playing() or self._vc.is_paused():
                self._vc.stop()

            # Disconnect from voice
            if self._vc.is_connected():
                await self._vc.disconnect()

            await asyncio.sleep(1)
            # Set the Voice Client to none
            self._vc = None

            # If the disconnect was forced
            if force:
                if reloaded:
                    await self.text_channel.send(('Disconnected due to a cog reload. '
                                                  'Please wait a minute or two then reconnect me'))

                else:
                    await self.text_channel.send('Disconnected from voice [Empty Voice Channel]')
                # Cancel the player task and tell cog this player can be removed
                self.audio_player.cancel()
                return True

            else:
                # Disconnect was done by a user
                await self.text_channel.send('Disconnected from the voice channel '
                                             f'by {user.mention}')

                # Cancel the player task and tell cog this player can be removed
                self.audio_player.cancel()
                return True

        else:
            await self.text_channel.send((f'Sorry {user.mention}, '
                                          'You need to be a mod or higher to disconnect me'))

            return False


    async def add_queue(self, ctx, link):
        ''' Adds link to the queue to be played '''

        # Check if the bot is in a channel to play music
        if self._vc is None:
            await ctx.send((f'{ctx.author.mention}, '
                            'I am not in a voice channel to play music. Please connect me first'))

        else:
            # Check if the user is in the same channel as the bot
            if ctx.author.voice is not None and ctx.author.voice.channel == self._vc.channel:
                start_pos = 1 # The start pos for playlists
                search = False # Used to tell ytdl that we are doing a youtube search

                # If youtube.com or yout.be is in link
                if 'youtube.com' in link or 'youtu.be' in link:
                    # Youtube
                    if 'youtu.be' in link:
                        # Change share link to normal link
                        vid_id = link.split('/')[-1]
                        link = 'https://www.youtube.com/watch?v=' + vid_id

                    elif '&index' in link:
                        # Get start pos for playlist
                        temp = link.split('&')
                        for i in range(0, len(temp)):
                            if 'index=' in temp[i]:
                                # Get start pos
                                start_pos = int(temp[i].replace('index=', '').strip())
                                break

                elif 'soundcloud.com' not in link:
                    # If it's not got soundcloud.com in it we will search for it
                    # Else it is soundclound and will play it
                    search = True

                # Download the info from the link
                # Set ytdl to use startpos and endpos to get info
                opts = {'format': 'webm[abr>0]/bestaudio/best',
                        'prefer_ffmpeg': True,
                        'no_warnings': True,
                        'ignoreerrors': True,
                        'quiet': True,
                        'playliststart': start_pos,
                        'playlistend': (start_pos + 19),
						'reconnect': 1,
						'reconnect_streamed': 1,
						'reconnect_delay_max' : 5
                       }

                if search:
                    ytdl = youtube_dl.YoutubeDL(dict(opts, **{'default_search': 'auto'}))
                else:
                    ytdl = youtube_dl.YoutubeDL(opts)

                # Send info message
                msg = 'Getting info from link. This might take a while please wait'
                await ctx.send(msg, delete_after=5)

                async with ctx.channel.typing():
                    # Make ytdl run in a async task so the command can be used multiple times
                    # Without it waiting for ytdl
                    func = functools.partial(ytdl.extract_info, link, download=False)
                    result = await self.bot.loop.run_in_executor(None, func)

                    if result is not None:
                        # Check if playlist was downloaded
                        if 'entries' in result:
                            queued = 0
                            duration = 0
                            for song in result['entries']:
                                # Get song info
                                if song is not None:
                                    self.queue.append(Song(ctx.author, song))
                                    duration += song['duration']
                                    queued += 1

                                else:
                                    log_msg = (f"Video in {link}, could not be downloaded. "
                                               f"Guild: {ctx.guild.name} ({ctx.guild.id})")

                                    self.bot.logger.warning(log_msg)

                            # Make the duration readable
                            mins, secs = divmod(duration, 60)

                            # If search term added as search always returns as it was in a playlist
                            if search:
                                msg = ':notes: Queued: `{0} [{1}:{2:02d}]` [Songs in queue: {3}]'
                                if self.paused_timeleft is not None:
                                    msg += ' Current song is *PAUSED*'

                                if result['entries'] is None:
                                    await ctx.send((f"Sorry {ctx.author.mention}, "
                                                    "that could not be downloaded"))

                                else:
                                    title = result['entries'][0]['title'].replace('`', "'")
                                    await ctx.send(msg.format(title, mins, secs, len(self.queue)))

                            else:
                                # Tell user how many songs were added
                                if queued > 0:
                                    msg = 'Queued: `{0} [{1}:{2:02d}]` songs [Songs in queue: {3}]'

                                else:
                                    msg = 'No songs were added'

                                if self.paused_timeleft is not None:
                                    msg += ' Current song is *PAUSED*'

                                await ctx.send(msg.format(str(queued), mins, secs, len(self.queue)))

                        else:
                            # Single song
                            # Get song url, title and requester
                            if result is not None:
                                # Add song to queue
                                self.queue.append(Song(ctx.author, result))

                                # Make the duration readable
                                mins, secs = divmod(result['duration'], 60)

                                # Tell the user the song has been queued
                                msg = ':notes: Queued: `{0} [{1}:{2:02d}]` [Songs in queue: {3}]'
                                if self.paused_timeleft is not None:
                                    msg += ' Current song is *PAUSED*'

                                title = result['title'].replace('`', "'")
                                await ctx.send(msg.format(title, mins, secs, len(self.queue)))

                            else:
                                # Tell the user if it couldn't be added
                                msg = 'Could not add that link to queue'
                                if self.paused_timeleft is not None:
                                    msg += ' Current song is *PAUSED*'

                                await ctx.send(msg)
                                log_msg = (f"Video in {link}, could not be downloaded. "
                                           f"Guild: {ctx.guild.name} ({ctx.guild.id})")

                                self.bot.logger.warning(log_msg)

                    else:
                        await ctx.send(f'Sorry {ctx.author.mention}, nothing was found from that')

                # Start player is not already playing
                if self.queue:
                    self.songs_in_queue.set()

            else:
                await ctx.send((f'{ctx.author.mention}, '
                                'You need to be in my voice channel to add a song'))

    async def skip(self, ctx, force=False):
        ''' Start the vote skip or force if done by admin using force skip command '''

        if ctx.author.voice is None:
            await ctx.channel.send((f'{ctx.author.mention}, '
                                    'You need to be in a voice channel to skip the song'))
        else:
            # Check if there is a music player and it is playing
            if self._vc.is_playing() or self._vc.is_paused():
                # Check if forced
                if force:
                    self.skips.clear()
                    self._vc.stop()
                    await ctx.send(f'{ctx.author.mention} has forced skipped the song')

                else:
                    # Check user hasn't already skipped
                    if ctx.author.id not in self.skips:
                        self.skips.add(ctx.author.id)
                        total_votes = len(self.skips)
                        skips_needed = round(len(self._vc.channel.members) * 0.6)

                        # It the number of enough to pass skip
                        if total_votes >= skips_needed:
                            self.skips.clear()
                            self._vc.stop()
                            await ctx.send((f'{ctx.author.mention} has voted to skip.\n'
                                            'The vote skip has passed.'))

                        else:
                            # Tell user they have voted to skip and how many left is needed
                            await ctx.send(f'{ctx.author.mention} has voted to skip [{total_votes}/{skips_needed}].')

                    else:
                        # Tell user they have already skipped
                        await ctx.send(f'{ctx.author.mention}, You have already voted to skip')

            else:
                # Send message saying there is nothing to skip
                await ctx.send(f'{ctx.author.mention}, There is nothing playing to be skipped')

    async def change_volume(self, ctx, percent):
        ''' Change the volume of the bot '''

        if ctx.author.voice is None:
            await ctx.channel.send((f'{ctx.author.mention}, '
                                    'You need to be in a voice channel to change the volume'))
        else:
            if int(percent) < 0 or int(percent) > 100:
                # Send user error message for invalid percentage
                err_msg = (f'{ctx.author.mention}, '
                            'Volume is done by percentage between 0%  and 100%, '
                            'Please pick a vaild percentage')

                await ctx.send(err_msg)

            else:
                # Change percentage to a valid number for ffmpeg or avconv
                self.volume = int(percent) / 100
                # Change volume
                self._vc.source.volume = self.volume
                # Send volume has been changed message
                await ctx.send(f'{ctx.author.mention}, Volume has been changed to: **{percent}%**')

    async def pause_music(self, ctx):
        ''' Pauses the music '''

        # Check if there is something playing and isn't already pasued
        if self._vc.is_playing() and not self._vc.is_paused():
            # Pause then calculate how much time was left in the song
            self._vc.pause()
            self.paused_timeleft = round(self.time_song_ends - time.time())
            await ctx.send(f':pause_button: **{self.current.title}** is now paused')

        else:
            await ctx.send(f'{ctx.author.mention}, There is nothing playing to be paused')

    async def resume_music(self, ctx):
        ''' Resume the music '''

        # Check if there is something pasued and not playing
        if self._vc.is_paused() and not self._vc.is_playing():
            # Calculate when the song ends form the time left then resume the song
            self.time_song_ends = time.time() + self.paused_timeleft
            self.paused_timeleft = None
            self._vc.resume()
            await ctx.send(f':arrow_forward:  **{self.current.title}** is now playing')

        else:
            await ctx.send(f'{ctx.author.mention}, There is nothing paused')

    async def clear_queue(self, ctx):
        ''' Clear the queue '''

        self.queue = []
        await ctx.send(f'{ctx.author.mention}, The queue has been cleared!!')

    async def now_playing(self, ctx):
        ''' Shows the current song that is playing and time left till next song
        '''

        # Nothing playing
        if self.current is None:
            await ctx.send(f'{ctx.author.mention}, There is nothing playing')

        else:
            # Get current duration if not paused
            if self.paused_timeleft is None:
                time_left = round(self.time_song_ends - time.time())
                current_dur = self.current.duration - time_left

            else:
                # Get current duration if pasued
                current_dur = self.current.duration - self.paused_timeleft

            # Split current duration in to hours, mins and seconds
            mins, secs = divmod(current_dur, 60)
            hours, mins = divmod(mins, 60)
            # Do the same for complete duration
            fmins, fsecs = divmod(self.current.duration, 60)
            fhours, fmins = divmod(fmins, 60)

            # Based on how many hours there is in the song create embed
            if fhours != 0:
                desc = (f'[{self.current.title}]({self.current.url}) '
                        f'[{hours:02d}:{mins:02d}:{secs:02d}/{fhours:02d}:{fmins:02d}:{fsecs:02d}]')

                np_embed = discord.Embed(type='rich',
                                         colour=discord.Colour(65280),
                                         description=desc)

            else:
                desc = (f'[{self.current.title}]({self.current.url}) '
                        f'[{mins:02d}:{secs:02d}/{fmins:02d}:{fsecs:02d}]')

                np_embed = discord.Embed(type='rich',
                                         colour=discord.Colour(65280),
                                         description=desc)

            # Change colour and author message based on if it paused or not
            if self.paused_timeleft is not None:
                np_embed.colour = discord.Colour(16711680)
                np_embed.set_author(name='Now Playing [PAUSED]:')

            else:
                np_embed.set_author(name='Now Playing:')

            # Put song requester in footer set thumbmail and send
            np_embed.set_footer(text='Requested by {0}'.format(self.current.requester.display_name))
            np_embed.set_thumbnail(url=self.current.thumbnail)
            await ctx.send(embed=np_embed)

    async def show_queue(self, ctx):
        ''' Show the next few songs in the queue
        '''

        # If the only the current playing song or nothing is queue tell user
        if not self.queue:
            await ctx.send(f'{ctx.author.mention}, There are no songs in the queue')

        else:
            # Get current duration if not paused
            if self.paused_timeleft is None:
                time_left = round(self.time_song_ends - time.time())
                current_dur = self.current.duration - time_left

            else:
                # Get current duration if pasued
                current_dur = self.current.duration - self.paused_timeleft

            # Split current duration in to hours, mins and seconds
            mins, secs = divmod(current_dur, 60)
            hours, mins = divmod(mins, 60)
            # Do the same for complete duration
            fmins, fsecs = divmod(self.current.duration, 60)
            fhours, fmins = divmod(fmins, 60)

            # Create the desc which tell the user the current song
            if fhours != 0:
                desc = (f'[{self.current.title}]({self.current.url}) '
                        f'[{hours:02d}:{mins:02d}:{secs:02d}/{fhours:02d}:{fmins:02d}:{fsecs:02d}]')

            else:
                desc = (f'[{self.current.title}]({self.current.url}) '
                        f'[{mins:02d}:{secs:02d}/{fmins:02d}:{fsecs:02d}]')

            # Check for more songs
            if self.queue:
                desc += '\nUp next:\n'

                # If there are 5 or lest song in queue only show them
                if len(self.queue) <= 5:
                    for i in range(len(self.queue)):
                        song = self.queue[i]
                        desc += (f'{i+1}:  [{song.title}]({song.url}) - '
                                 f'Requested by **{song.requester.display_name}**\n')

                else:
                    # Show the next 5 songs
                    for i in range(5):
                        song = self.queue[i]
                        desc += (f'{i+1}:  [{song.title}]({song.url}) - '
                                 f'Requested by **{song.requester.display_name}**\n')

                    # Display number of other songs
                    left = len(self.queue[5:])
                    desc += f'And **{left}** more'

                total_dur = 0
                for song in self.queue:
                    total_dur += song.duration

                # Get queue total duration
                tmins, tsecs = divmod(total_dur, 60)
                thours, tmins = divmod(tmins, 60)

                if thours != 0:
                    desc += f'\n Total Duration: `{thours:02d}:{tmins:02d}:{tsecs:02d}`'
                else:
                    desc += f'\n Total Duration: `{tmins:02d}:{tsecs:02d}`'

            # Send embed
            qembed = discord.Embed(type='rich', colour=discord.Colour(5577355), description=desc)
            qembed.set_author(name='Currently Playing:')
            await ctx.send(embed=qembed)

    def toggle_next(self, error):
        ''' Used to tell the audio player that the song is done and the next one can be played
        '''

        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        '''
        Background task that waits for a song to be in the queue
        Before playing the song
        '''

        while True:
            # Wait until songs are in the queue
            await self.songs_in_queue.wait()
            self.songs_in_queue.clear()
            self.play_next_song.clear()
            # Get the current song
            self.current = self.queue.pop(0)

            # Get hours, mins and seconds from duration
            mins, secs = divmod(int(self.current.duration), 60)
            hour, mins = divmod(mins, 60)

            # Create playing embed
            desc = f'[{self.current.title}]({self.current.url}) ({hour:02d}:{mins:02d}:{secs:02d}s)'
            npembed = discord.Embed(type='rich',
                                    colour=discord.Colour(65280),
                                    description=desc)

            npembed.set_author(name='Now Playing:')
            npembed.set_footer(text=f'Requested by {self.current.requester.display_name}')
            npembed.set_thumbnail(url=self.current.thumbnail)

            # Send the now playing embed and start player
            await self.text_channel.send(embed=npembed)
            await asyncio.sleep(1)

            # Start the player and wait until it is done
            # Check if the user want to use avconv instead of ffmpeg
            # Create the before args to stop the song from ending before the end
            before_args = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            if self.bot.config['use_avconv']:
                self._vc.play(discord.FFmpegPCMAudio(self.current.download_url, executable='avconv'),
                            after=self.toggle_next)

            else:
                self._vc.play(discord.FFmpegPCMAudio(self.current.download_url, before_options=before_args),
                            after=self.toggle_next)

            # Change the volume of the audio
            self._vc.source = discord.PCMVolumeTransformer(self._vc.source, volume=self.volume)
            # Calculate when the song should end for np message then wait for next song
            self.time_song_ends = time.time() + self.current.duration
            await self.play_next_song.wait()

            # If more songs in queue make it play and not wait
            if self.queue:
                self.songs_in_queue.set()

            # Reset skip
            self.skips.clear()
            self.current_song = None

class Music(commands.Cog):
    '''
    Music player
    Create a server music player upon connect command which if music channel is forced
    '''

    def __init__(self, bot):
        self.bot = bot
        self.musicplayers = {}
        self.music_channels = utils.check_cog_config(self, 'music_channels.json')

    def __unload(self):
        # Remove listener for when every one leaves the voice without disconnecting bot
        self.bot.remove_listener(self.on_voice_state_update, "on_voice_state_update")

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
        '''Sets the channel command is typed in as the music channel for that server '''

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
        utils.save_cog_config(self, 'music_channels.json', self.music_channels)

        # Tell the user the right message
        if removed:
            await ctx.send('This channel is no longer the music channel for the server.')
            log_msg = (f'Flandre/data/music/music_channels.json has been saved. '
                       f'Reason: {ctx.channel.name} ({ctx.channel.id}) '
                       'is no longer a logging channel')

            self.bot.logger.info(log_msg)

        else:
            await ctx.send('This channel has been made the music channel for the server.')
            log_msg = (f'Flandre/data/music/music_channels.json has been saved. '
                       f'Reason: {ctx.channel.name} ({ctx.channel.id}) '
                       'has been made a logging channel')

            self.bot.logger.info(log_msg)

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
                self.bot.logger.info(f'Created Music Player for {ctx.guild.name} ({ctx.guild.id})')
                await self.musicplayers[str(ctx.guild.id)].connect(ctx)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    # Create the music player for the guild and connect it
                    self.musicplayers[str(ctx.guild.id)] = MusicPlayer(self.bot)
                    log_msg = f'Created Music Player for {ctx.guild.name} ({ctx.guild.id})'
                    self.bot.logger.info(log_msg)
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
                    self.bot.logger.info(log_msg)

            else:
                # Check if the channel is the forced music channel
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    # Disconnect the bot and delete the player if successful
                    done = await self.musicplayers[str(ctx.guild.id)].disconnect(ctx.author)
                    if done:
                        del self.musicplayers[str(ctx.guild.id)]
                        log_msg = f'Removed Music Player for {ctx.guild.name} ({ctx.guild.id})'
                        self.bot.logger.info(log_msg)

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

        if str(guild.id) in self.musicplayers and member.id != self.bot.user.id:
            voice = self.musicplayers[str(guild.id)]._vc
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
                        self.bot.logger.info(f'Removed Music Player for {guild.name} ({guild.id})')
            else:
                if str(guild.id) in self.musicplayers:
                    total_votes = len(voice.skips)
                    skips_needed = round(len(voice.channel.members) * 0.6)
                    # It the number of enough to pass skip
                    if total_votes >= skips_needed:
                        voice.skips.clear()
                        voice._vc.stop()
                        channel = voice.text_channel
                        await channel.send('A user has left the channel, and the skips needed now match'
                                        ' the current number of skips!! Skipping song')



def setup(bot):
    ''' Setup to add cog to bot'''
    cog = Music(bot)
    bot.add_listener(cog.on_voice_state_update, "on_voice_state_update")
    bot.add_cog(cog)
