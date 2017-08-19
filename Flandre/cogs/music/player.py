''' Holds the classes for song and the music player for the cog '''

import asyncio
import functools
import logging
import time

import discord
import youtube_dl

logger = logging.getLogger(__package__)

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
        self.vc = None
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
        # Task for auto leave if no song has been played for a while
        self.auto_leave = None
    
    def check_mod(self, user):
        '''
        Check if user is mod needed as some admin commands can be used by non-admins
        Such as if bot is not connected such as the first connect
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
            if self.vc is None:
                # Check if voice is still connected somehow
                for vc in self.bot.voice_clients:
                    if vc.guild == ctx.guild:
                        self.vc = vc
                        self.text_channel = ctx.channel

                        # Check if something is playing
                        if self.vc.is_playing or self.vc.is_paused:
                            self.vc.stop()

                        # Tell the user we have connected and bound messages to the channel
                        await ctx.send((f'Connected to **{self.vc.channel.name}** '
                                        'and bound to this text channel'))

                        break

                else:
                    # No voice client means bot is not connected so anyone can connect bot
                    # Connect to that voice channel
                    self.vc = await ctx.author.voice.channel.connect()
                    # Set text channel to the channel the message was sent in
                    self.text_channel = ctx.channel
                    # Tell the user we have connected and bound messages to the channel
                    await ctx.send((f'Connected to **{self.vc.channel.name}** '
                                    'and bound to this text channel'))

            else:
                # The bot is currently connected and needs to be move to a different channel
                # This can only be done by mods and above so we need to check that
                if self.check_mod(ctx.author):
                    # Check if the person asking the bot to move is not in the same channel
                    if ctx.author.voice.channel == self.vc.channel:
                        await ctx.send(f'{ctx.author.mention}, I am already in your voice channel')

                    else:
                        # Move to that channel
                        await self.vc.move_to(ctx.author.voice.channel)
                        # Set text channel to the channel the message was sent in
                        self.text_channel = ctx.channel
                        # Tell the user we have moved and bound messages to the channel
                        await ctx.send((f'Moved to **{self.vc.channel.name}** '
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
            if self.vc.is_playing() or self.vc.is_paused():
                self.vc.stop()

            # Disconnect from voice
            if self.vc.is_connected():
                await self.vc.disconnect()

            await asyncio.sleep(1)
            # Set the Voice Client to none
            self.vc = None

            # If the disconnect was forced
            if force:
                if reloaded:
                    await self.text_channel.send(('Disconnected due to a cog reload. '
                                                  'Please wait a minute or two then reconnect me'))

                else:
                    await self.text_channel.send('Force disconnected from voice')
                # Cancel the player task and tell cog this player can be removed
                self.audio_player.cancel()
                if self.auto_leave is not None:
                    self.auto_leave.cancel()
                    self.auto_leave = None
                
                return True

            else:
                # Disconnect was done by a user
                await self.text_channel.send('Disconnected from the voice channel '
                                             f'by {user.mention}')

                # Cancel the player task and tell cog this player can be removed
                self.audio_player.cancel()
                if self.auto_leave is not None:
                    self.auto_leave.cancel()
                    self.auto_leave = None

                return True

        else:
            await self.text_channel.send((f'Sorry {user.mention}, '
                                          'You need to be a mod or higher to disconnect me'))

            return False

    async def add_queue(self, ctx, link):
        ''' Adds link to the queue to be played '''

        # Check if the bot is in a channel to play music
        if self.vc is None:
            await ctx.send((f'{ctx.author.mention}, '
                            'I am not in a voice channel to play music. Please connect me first'))

        else:
            # Check if the user is in the same channel as the bot
            if ctx.author.voice is not None and ctx.author.voice.channel == self.vc.channel:
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
                        'playlistend': (start_pos + 19)
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

                                    logger.warning(log_msg)

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

                                logger.warning(log_msg)

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
            if self.vc.is_playing() or self.vc.is_paused():
                # Check if forced
                if force:
                    self.skips.clear()
                    self.vc.stop()
                    await ctx.send(f'{ctx.author.mention} has forced skipped the song')

                else:
                    # Check user hasn't already skipped
                    if ctx.author.id not in self.skips:
                        self.skips.add(ctx.author.id)
                        total_votes = len(self.skips)
                        skips_needed = round(len(self.vc.channel.members) * 0.6)

                        # It the number of enough to pass skip
                        if total_votes >= skips_needed:
                            self.skips.clear()
                            self.vc.stop()
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
                self.vc.source.volume = self.volume
                # Send volume has been changed message
                await ctx.send(f'{ctx.author.mention}, Volume has been changed to: **{percent}%**')

    async def pause_music(self, ctx):
        ''' Pauses the music '''

        # Check if there is something playing and isn't already pasued
        if self.vc.is_playing() and not self.vc.is_paused():
            # Pause then calculate how much time was left in the song
            self.vc.pause()
            self.paused_timeleft = round(self.time_song_ends - time.time())
            await ctx.send(f':pause_button: **{self.current.title}** is now paused')

        else:
            await ctx.send(f'{ctx.author.mention}, There is nothing playing to be paused')

    async def resume_music(self, ctx):
        ''' Resume the music '''

        # Check if there is something pasued and not playing
        if self.vc.is_paused() and not self.vc.is_playing():
            # Calculate when the song ends form the time left then resume the song
            self.time_song_ends = time.time() + self.paused_timeleft
            self.paused_timeleft = None
            self.vc.resume()
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

        self.auto_leave = self.bot.loop.create_task(self.auto_leave_task())
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def auto_leave_task(self):
        '''
        Leave the voice after 5 mins of no music
        '''

        await asyncio.sleep(300)
        await self.text_channel.send('No music has been added for 5 mins. Disconnected')
        await self.disconnect(self.bot.user, force=True)
    
    async def audio_player_task(self):
        '''
        Background task that waits for a song to be in the queue
        Before playing the song
        '''

        while True:
            # Wait until songs are in the queue
            await self.songs_in_queue.wait()
            if self.auto_leave is not None:
                self.auto_leave.cancel()
                self.auto_leave = None
            
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
                self.vc.play(discord.FFmpegPCMAudio(self.current.download_url, executable='avconv'),
                             after=self.toggle_next)

            else:
                self.vc.play(discord.FFmpegPCMAudio(self.current.download_url, before_options=before_args),
                             after=self.toggle_next)

            # Change the volume of the audio
            self.vc.source = discord.PCMVolumeTransformer(self.vc.source, volume=self.volume)
            # Calculate when the song should end for np message then wait for next song
            self.time_song_ends = time.time() + self.current.duration
            await self.play_next_song.wait()

            # If more songs in queue make it play and not wait
            if self.queue:
                self.songs_in_queue.set()

            # Reset skip
            self.skips.clear()
            self.current_song = None
