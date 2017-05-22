import discord
from discord.ext import commands
import youtube_dl
import asyncio
import functools
from .. import permissions, utils
import time


class Song:
    ''' Song Class used to store song information in the queue so it can be easily accessed
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
    ''' Music Player Class
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
        self.volume = 0.20
        self.skips = set()
        # asyncio Events for if there are songs in queue and if the next song is to be played
        self.play_next_song = asyncio.Event()
        self.songs_in_queue = asyncio.Event()
        # Timestamp for when the song ends
        self.time_song_ends = None
        # Time left in seconds when the song is paused to get the new end timestamp
        self.paused_timeleft = None
        # Background task that plays the music for the server
        self.audio_player = self.bot.loop.create_task(self.audioPlayer())

    def checkMod(self, user):
        ''' Check if user is mod needed as some admin commands can be used by non-admins
            if bot is not connected such as the first connect
        '''
        
        if user.id in self.bot.config['ownerid']:
            return True
        
        elif self.text_channel.permissions_for(user).manage_guild or self.text_channel.permissions_for(user).manage_channels:
            return True
        
        else:
            return False

    async def connect(self, ctx):
        ''' Connects Bot to voice channel if not in one
            Move to channel if in already in one
        '''

        # Check the user is connected to voice
        if ctx.author.voice is None:
            await channel.send(f'{user.mention}, You need to be in a voice channel so I can connect to it')
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
                        await ctx.send(f'Connected to **{self._vc.channel.name}** and bound to this text channel')
                        break

                else:
                    # No voice client means bot is not connected so anyone can connect bot
                    # Connect to that voice channel
                    self._vc = await ctx.author.voice.channel.connect()
                    # Set text channel to the channel the message was sent in
                    self.text_channel = ctx.channel
                    # Tell the user we have connected and bound messages to the channel
                    await ctx.send(f'Connected to **{self._vc.channel.name}** and bound to this text channel')
            
            else:
                # The bot is currently connected and needs to be move to a different channel
                # This can only be done my mods and above so we need to check that
                if self.checkMod(ctx.author):
                    # Check if the person asking the bot to move is not in the same channel
                    if ctx.author.voice.channel == self._vc.channel:
                        await ctx.send(f'{ctx.author.mention}, I am already in your voice channel')
                    
                    else:
                        # Move to that channel
                        await self._vc.move_to(ctx.author.voice.channel)
                        # Set text channel to the channel the message was sent in
                        self.text_channel = ctx.channel
                        # Tell the user we have moved and bound messages to the channel
                        await ctx.send(f'Moved to **{self._vc.channel.name}** and bound to this text channel')

                else:
                    # User is not mod or above so tell user they cannot move the bot
                    await ctx.send(f'Sorry {ctx.author.mention}, You need to be a mod or above to move me if I am already connected')

    async def disconnect(self, user, force=False, reloaded=False):
        ''' Disconnect the bot from the voice channel (mod only)
            If no one is in the voice channel the bot forces the disconnect using force
            If a cog reload happens force and reload are used to tell the users using bot that a disconnect happened due to a reload
            This shouldn't happen unless the reload is really needed
            Return True if sucessful so the music player can be removed else return False
        '''

        # Check if the disconnect was forced or done by a mod+
        if force or self.checkMod(user):
            # Clear the queue
            self.queue = []
            
            # Check if the voice client is playing or paused
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
                    await self.text_channel.send('Disconnected due to a cog reload. Please wait a minute or two then reconnect me')
                else:
                    await self.text_channel.send('Disconnected from voice [Empty Voice Channel]')
                self.audio_player.cancel()
                return True
            
            else:
                # Disconnect was done by a user
                await self.text_channel.send(f'Disconnected from the voice channel by {user.display_name}')
                self.audio_player.cancel()
                return True

        else:
            await ctx.send(f'Sorry {user.mention}, You need to be a mod or higher to disconnect me')
            return False


    async def addQueue(self, ctx, link):
        ''' Adds link to the queue to be played
        '''

        if self._vc is None:
            await ctx.send(f'{ctx.author.mention}, I am not in a voice channel to play music. Please connect me first')
        
        else:
            if ctx.author.voice is not None and ctx.author.voice.channel == self._vc.channel:
                start_pos = 1 # The start pos for playlists
                search = False

                if 'youtube.com' in link or 'youtu.be' in link:
                    # Youtube
                    if 'youtu.be' in link:
                        # Change share link to normal link
                        vidID = link.split('/')[-1]
                        link = 'https://www.youtube.com/watch?v=' + vidID
                    elif '&index' in link:
                        # Get start pos for playlist
                        temp = link.split('&')
                        for i in range(0, len(temp)):
                            if 'index=' in temp[i]:
                                # Get start pos and end pos
                                start_pos = int(temp[i].replace('index=', '').strip())
                                break

                elif 'soundcloud.com' not in link:
                    # If it's not got soundcloud.com in it we will search for it else it is soundclound and will play it
                    search = True
                
                # Download the info from the link
                # Set ytdl to use startpos and endpos to get info
                if search:
                    ytdl = youtube_dl.YoutubeDL({'format': 'webm[abr>0]/bestaudio/best', 'prefer_ffmpeg': True, 'default_search': 'auto' , 'no_warnings': True, 'ignoreerrors': True, 'quiet': True})
                else:
                    ytdl = youtube_dl.YoutubeDL({'format': 'webm[abr>0]/bestaudio/best', 'prefer_ffmpeg': True,'playliststart': start_pos, 'playlistend': (start_pos + 19) , 'no_warnings': True, 'ignoreerrors': True, 'quiet': True})

                # Send info message
                msg = 'Getting info from link. This might take a while please wait'
                await ctx.send(msg, delete_after=5)

                async with ctx.channel.typing():
                    func = functools.partial(ytdl.extract_info, link, download=False)
                    result = await self.bot.loop.run_in_executor(None, func)

                    # Check if playlist was downloaded
                    if 'entries' in result:
                        queued = 0
                        for song in result['entries']:  
                            # Get song info
                            if song is not None:
                                self.queue.append(Song(ctx.author, song))
                                queued += 1
                            else:
                                self.bot.logger.warning(f"Video in {link}, could not be downloaded. Guild: {ctx.guild.name} ({ctx.guild.id})")

                        # If search term added as search always returns as it was in a playlist
                        if search:
                            msg = ':notes: Queued: **{0}**'
                            if self.paused_timeleft is not None:
                                msg += ' Current song is *PAUSED*'
                            
                            if result['entries'] is None:
                                await ctx.send(f"Video {link}, could not be downloaded")
                            else:
                                await ctx.send(msg.format(result['entries'][0]['title']))
                        
                        else:
                            if queued > 0:
                                msg = 'Queued: **{0}** songs [Songs in queue: {1}]'
                            
                            else:
                                msg = 'No songs were added'
                            
                            if self.paused_timeleft is not None:
                                msg += ' Current song is *PAUSED*'
                            
                            await ctx.send(msg.format(str(queued), len(self.queue)))
                    else:
                        # Single song
                        # Get song url, title and requester
                        if result is not None:                    
                            # Add song to queue
                            self.queue.append(Song(ctx.author, result))
                            
                            # Tell the user the song has been queued
                            msg = ':notes: Queued: **{0}** [Songs in queue: {1}]'
                            if self.paused_timeleft is not None:
                                msg += ' Current song is *PAUSED*'
                            
                            await ctx.send(msg.format(result['title'], len(self.queue)))
                        
                        else:
                            msg = 'Could not add that link to queue'
                            if self.paused_timeleft is not None:
                                msg += ' Current song is *PAUSED*'
                            
                            await ctx.send(msg)
                            self.bot.logger.warning(f"Video in {link}, could not be downloaded. Guild: {ctx.guild.name} ({ctx.guild.id})")

                # Start player is not already playing
                if len(self.queue) != 0:
                    self.songs_in_queue.set()

            else:
                await ctx.send(f'{ctx.author.mention}, You need to be in my voice channel to add a song')

    async def skip(self, ctx, force=False):
        ''' Start the vote skip or force if done by admin using force skip command
        '''

        # Check if there is a music player and it is playing
        if self._vc.is_playing() or self._vc.is_paused():
            # Check if forced
            if force:
                self.skips.clear()
                self._vc.stop()
                await ctx.send(f'**{ctx.author.display_name}** has forced skipped the song')                
            
            else:
                if ctx.author.id not in self.skips:
                    self.skips.add(ctx.author.id)
                    total_votes = len(self.skips)
                    
                    if total_votes >= 3:
                        self.skips.clear()
                        self._vc.stop()
                        await ctx.send(f'**{ctx.author.display_name}** has voted to skip.\nThe vote skip has passed.')
                    
                    else:
                        await ctx.send(f'**{ctx.author.display_name}** has voted to skip [{total_votes}/3].')
                
                else:
                    await ctx.send(f'{ctx.author.mention}, You have already voted to skip')

        else:
            # Send message saying there is nothing to skip
            await ctx.send(f'{ctx.author.mention}, There is nothing playing to be skipped')

    async def changeVolume(self, ctx, percent):
        ''' Change the volume of the bot
        '''

        if int(percent) < 0 or int(percent) > 200:
            # Send user error message for invalid percentage
            await ctx.send(f'{ctx.author.mention}, Volume is done by percentage between 0%  and 200%, Please pick a vaild percentage')
        
        else:
            # Change percentage to a valid number for ffmpeg or avconv
            self.volume = int(percent) / 100                        
            # Change volume
            self._vc.source.volume=self.volume                    
            # Send volume has been changed message
            await ctx.send(f'{ctx.author.mention}, Volume has been changed to: **{percent}%**')

    async def pauseMusic(self, ctx):
        ''' Pauses the music 
        '''
        
        if self._vc.is_playing() and not self._vc.is_paused():
            self._vc.pause()
            self.paused_timeleft = round(self.time_song_ends - time.time())
            await ctx.send(f':pause_button: **{self.current.title}** is now paused')
        
        else:
            await ctx.send(f'{ctx.author.mention}, There is nothing playing to be paused')

    async def resumeMusic(self, ctx):
        ''' Resume the music 
        '''

        if self._vc.is_paused() and not self._vc.is_playing():
            self.time_song_ends = time.time() + self.paused_timeleft
            self.paused_timeleft = None
            self._vc.resume()
            await ctx.send(f':arrow_forward:  **{self.current.title}** is now playing')
        
        else:
            await ctx.send(f'{ctx.author.mention}, There is nothing paused')

    async def clearQueue(self, ctx):
        ''' Clear the queue 
        '''
        
        self.queue = []
        await ctx.send(f'{ctx.author.mention}, The queue has been cleared!!')

    async def nowPlaying(self, ctx):
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
            m, s = divmod(current_dur, 60)
            h, m = divmod(m, 60)
            # Do the same for complete duration
            fm, fs = divmod(self.current.duration, 60)
            fh, fm = divmod(fm, 60)
            
            # Based on how many hours there is in the song create embed
            if fh != 0:
                np = discord.Embed(type='rich', colour=discord.Colour(65280), description='[{0.title}]({0.url}) [{1:02d}:{2:02d}:{3:02d}/{4:02d}:{5:02d}:{6:02d}]'.format(self.current, h, m, s, fh, fm, fs))
            else:
                np = discord.Embed(type='rich', colour=discord.Colour(65280), description='[{0.title}]({0.url}) [{1:02d}:{2:02d}/{3:02d}:{4:02d}]'.format(self.current, m, s, fm, fs))
            
            # Change colour and author message based on if it paused or not
            if self.paused_timeleft is not None:
                np.colour = discord.Colour(16711680)
                np.set_author(name='Now Playing [PAUSED]:')
            else:
                np.set_author(name='Now Playing:')
            
            # Put song requester in footer set thumbmail and send
            np.set_footer(text='Requested by {0}'.format(self.current.requester.display_name))
            np.set_thumbnail(url=self.current.thumbnail)
            await ctx.send(embed=np)

    async def showQueue(self, ctx):
        ''' Show the next few songs in the queue
        '''

        # If the only the current playing song or nothing is queue tell user
        if len(self.queue) == 0:
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
            m, s = divmod(current_dur, 60)
            h, m = divmod(m, 60)
            # Do the same for complete duration
            fm, fs = divmod(self.current.duration, 60)
            fh, fm = divmod(fm, 60)

            if fh != 0:
                desc = '[{0.title}]({0.url}) [{1:02d}:{2:02d}:{3:02d}/{4:02d}:{5:02d}:{6:02d}]'.format(self.current, h, m, s, fh, fm, fs) 
            else:
                desc = '[{0.title}]({0.url}) [{1:02d}:{2:02d}/{3:02d}:{4:02d}]'.format(self.current, m, s, fm, fs)
            
            # Check for more songs
            if len(self.queue) > 1:
                desc += '\nUp next:\n'
                if len(self.queue) <= 5:
                    for i in range(len(self.queue)):
                        desc += '{0}:  [{1.title}]({1.url}) - Requested by **{1.requester.display_name}**\n'.format((i+1), self.queue[i])
                
                else:
                    for i in range(5):
                        desc += '{0}:  [{1.title}]({1.url}) - Requested by **{1.requester.display_name}**\n'.format((i+1), self.queue[i])
                    
                    # Display number of other songs
                    desc += 'And **{0}** more'.format(len(self.queue[5:]))

            # Send embed
            qe = discord.Embed(type='rich', colour=discord.Colour(5577355), description=desc)
            qe.set_author(name='Currently Playing:')
            await ctx.send(embed=qe)

    def toggle_next(self, error):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audioPlayer(self):
        ''' Background task that waits for a song to be in the queue
            before playing the song
        '''

        while True:
            # Wait until songs are in the queue
            await self.songs_in_queue.wait()
            self.songs_in_queue.clear()
            self.play_next_song.clear()
            self.current = self.queue.pop(0)
            
            # Get hours, mins and seconds
            m, s = divmod(int(self.current.duration), 60)
            h, m = divmod(m, 60)
            
            # Create playing embed
            np = discord.Embed(type='rich', colour=discord.Colour(65280), description='[{0.title}]({0.url}) ({1:02d}:{2:02d}:{3:02d}s)'.format(self.current, h, m, s))
            np.set_author(name='Now Playing:')
            np.set_footer(text='Requested by {0}'.format(self.current.requester.display_name))
            np.set_thumbnail(url=self.current.thumbnail)
            # Send the now playing embed and start player
            await self.text_channel.send(embed=np)
            # Start the player and wait until it is done
            self._vc.play(discord.FFmpegPCMAudio(self.current.download_url), after=self.toggle_next)
            self._vc.source = discord.PCMVolumeTransformer(self._vc.source, volume=self.volume)
            self.time_song_ends = time.time() + self.current.duration
            await self.play_next_song.wait()
            # If more songs in queue make it play and not wait
            if len(self.queue) != 0:
                self.songs_in_queue.set()
            # Reset skip
            self.skips.clear()
            self.current_song = None

class music:
    ''' Music player
        Create a server music player upon connect command which if music channel is forced
    '''

    def __init__(self, bot):
        self.bot = bot
        self.musicplayers = {}
        self.music_channels = utils.checkCogConfig(self, 'music_channels.json')

    def __unload(self):
        self.bot.remove_listener(self.on_voice_state_update, "on_voice_state_update")

        for guild, player in self.musicplayers.copy().items():
            asyncio.ensure_future(player.disconnect(self.bot.user, force=True, reloaded=True))
            self.bot.logger.info(f'Forcefully deleted {guild} music player')
            del self.musicplayers[guild]

    @commands.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def setmusicchannel(self, ctx):
        '''Sets the channel command is typed in as the music channel for that server
        '''

        # Add or remove a channel as a music channel
        removed = False
        if str(ctx.guild.id) in self.music_channels:
            self.music_channels.pop(str(ctx.guild.id))
            removed = True
        else:
            self.music_channels[str(ctx.guild.id)] = ctx.channel.id

        utils.saveCogConfig(self, 'music_channels.json', self.music_channels)
        
        if removed:
            await ctx.send('This channel is no longer the music channel for the server.')
            self.bot.logger.info(f'Flandre/data/music/music_channels.json has been saved. Reason: {ctx.channel.name} ({ctx.channel.id}) is no longer a logging channel')
        else:
            await ctx.send('This channel has been made the music channel for the server.')
            self.bot.logger.info(f'Flandre/data/music/music_channels.json has been saved. Reason: {ctx.channel.name} ({ctx.channel.id}) has been made a logging channel')

    @commands.command()
    @commands.guild_only()
    async def connect(self, ctx):
        ''' Connects Bot to voice channel if not in one. Moves to channel if in already in one
        '''

        
        if str(ctx.guild.id) not in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                self.musicplayers[str(ctx.guild.id)] = MusicPlayer(self.bot)
                self.bot.logger.info(f'Created Music Player for {ctx.guild.name} ({ctx.guild.id})')
                await self.musicplayers[str(ctx.guild.id)].connect(ctx)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    self.musicplayers[str(ctx.guild.id)] = MusicPlayer(self.bot)
                    self.bot.logger.info(f'Created Music Player for {ctx.guild.name} ({ctx.guild.id})')
                    await self.musicplayers[str(ctx.guild.id)].connect(ctx)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                await self.musicplayers[str(ctx.guild.id)].connect(ctx)
                
            else:
                music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                await ctx.send(f'Music commands need to be done in {music_channel.mention}')


    @commands.command()
    @commands.guild_only()
    async def disconnect(self, ctx):
        ''' Disconnect the bot from the voice channel (mod only)
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                done = await self.musicplayers[str(ctx.guild.id)].disconnect(ctx.author)
                if done:
                    del self.musicplayers[str(ctx.guild.id)]
                    self.bot.logger.info(f'Removed Music Player for {ctx.guild.name} ({ctx.guild.id})')
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    done = await self.musicplayers[str(ctx.guild.id)].disconnect(ctx.author)
                    if done:
                        del self.musicplayers[str(ctx.guild.id)]
                        self.bot.logger.info(f'Removed Music Player for {ctx.guild.name} ({ctx.guild.id})')
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    async def add(self, ctx, link : str):
        ''' Add command <Youtube Link/Soundcloud Link/Search term>
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].addQueue(ctx, link)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].addQueue(ctx, link)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    async def skip(self, ctx):
        ''' Vote skip
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].skip(ctx)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].skip(ctx)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def forceskip(self, ctx):
        ''' Force skip
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].skip(ctx, force=True)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].skip(ctx, force=True)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command(aliases=["vol"])
    @commands.guild_only()
    @permissions.checkMod()
    async def volume(self, ctx, percent : int):
        ''' Volume command <0 - 200 %>
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].changeVolume(ctx, percent)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].changeVolume(ctx, percent)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def pause(self, ctx):
        ''' Pause current song
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].pauseMusic(ctx)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].pauseMusic(ctx)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def resume(self, ctx):
        ''' Resume current song
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].resumeMusic(ctx)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].resumeMusic(ctx)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    @permissions.checkMod()
    async def clear(self, ctx):
        ''' Clear the queue
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].clearQueue(ctx)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].clearQueue(ctx)

                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command()
    @commands.guild_only()
    async def queue(self, ctx):
        ''' Show next few songs in the queue
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].showQueue(ctx)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].showQueue(ctx)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    @commands.command(aliases=["np"])
    @commands.guild_only()
    async def nowplaying(self, ctx):
        ''' Show current playing song 
        '''

        if str(ctx.guild.id) in self.musicplayers:
            if str(ctx.guild.id) not in self.music_channels:
                await self.musicplayers[str(ctx.guild.id)].nowPlaying(ctx)
            
            else:
                if ctx.channel.id == self.music_channels[str(ctx.guild.id)]:
                    await self.musicplayers[str(ctx.guild.id)].nowPlaying(ctx)
                
                else:
                    music_channel = self.bot.get_channel(self.music_channels[str(ctx.guild.id)])
                    await ctx.send(f'Music commands need to be done in {music_channel.mention}')
        
        else:
            await ctx.send(f"{ctx.author.mention}, I am currently not connected to a voice channel")

    async def on_voice_state_update(self, member, before, after):
        ''' When voice channel update happens 
        '''
        if before.channel is None:
            guild = after.channel.guild
        else:
            guild = before.channel.guild

        if str(guild.id) in self.musicplayers and member.id != self.bot.user.id:
            vc = self.musicplayers[str(guild.id)]._vc
            channelmembers = vc.channel.members
            
            # Do a check then wait 10 seconds if true
            if len(channelmembers) == 1:
                await asyncio.sleep(5)
                
                # Do check again
                channelmembers = vc.channel.members
                if len(channelmembers) == 1:
                    done = await self.musicplayers[str(guild.id)].disconnect(self.bot.user, force=True)
                    
                    if done:
                        if str(guild.id) in self.musicplayers:
                            del self.musicplayers[str(guild.id)]
                        self.bot.logger.info(f'Removed Music Player for {guild.name} ({guild.id})')

def setup(bot):
    n = music(bot)
    bot.add_listener(n.on_voice_state_update, "on_voice_state_update")
    bot.add_cog(n)