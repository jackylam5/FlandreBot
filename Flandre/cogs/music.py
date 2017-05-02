import discord
from discord.ext import commands
import youtube_dl
import asyncio
from os import mkdir
from os.path import isdir
from Flandre import permissions
import json
import time

class Song:
    ''' Song Class used to store song information in the queue so it can be easily accessed
    '''
    def __init__(self, url, title, thumbnail, requester):
        self.url = url
        self.title = title
        self.thumbnail = thumbnail
        self.requester = requester

class MusicPlayer:
    ''' Music Player Class
        Manages connecting and disconnecting of the bot to that server
        Also manages adding and playing of songs
    '''

    def __init__(self, bot, server):
        # The bot and the server this music player is for
        self.bot = bot
        self.server = server
        # Channel to post now playing to (default to the servers default channel)
        self.text_channel = server.default_channel
        # Voice connection and the actual player(youtube-dl) for the server
        self.voice = None
        self.player = None
        # asyncio Events for if there are songs in queue and if the next song is to be played
        self.play_next_song = asyncio.Event()
        self.songs_in_queue = asyncio.Event()
        # Player volume - 1 is 100% (Max: 2, Min: 0)
        self.volume = 0.15
        # Queue and current song
        self.queue = []
        self.current_song = None
        # Duration used to get how long the song has left for show queue and now playing
        self.time_song_ends = None
        self.time_left_paused = None
        # Skips
        self.skips = set()
        self.audio_player = self.bot.loop.create_task(self.audioPlayer())

    def toggle_next(self):
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
            self.current_song = self.queue.pop(0)
            # Make youtube_dl download song
            kwargs = {'use_avconv': False}
            self.player = await self.voice.create_ytdl_player(self.current_song.url, ytdl_options={'quiet': True}, after=self.toggle_next, **kwargs)
            # Set volume
            self.player.volume = self.volume
            # Get hours, mins and seconds
            m, s = divmod(int(self.player.duration), 60)
            h, m = divmod(m, 60)
            # Create playing embed
            np = discord.Embed(type='rich', colour=discord.Colour(65280), description='**{0}** ({1:02d}:{2:02d}:{3:02d}s)'.format(self.player.title, h, m, s))
            np.set_author(name='Now Playing:', url=self.player.url)
            np.set_footer(text='Requested by {0}'.format(self.current_song.requester.display_name))
            np.set_thumbnail(url=self.current_song.thumbnail)
            # Send the now playing embed and start player
            await self.bot.send_message(self.text_channel, embed=np)
            # Start the player and wait until it is done
            self.player.start()
            self.time_song_ends = time.time() + self.player.duration
            await self.play_next_song.wait()
            # If more songs in queue make it play and not wait
            if len(self.queue) != 0:
                self.songs_in_queue.set()
            # Reset skip
            self.skips.clear()
            self.current_song = None


    def checkMod(self, user):
        ''' Check if user is mod needed as some admin commands can be used by non-admins
            if bot is not connected 
        '''
        
        if user.id in self.bot.config['ownerid']:
            return True
        elif user.permissions_in(self.text_channel).manage_server or user.permissions_in(self.text_channel).manage_channels:
            return True
        else:
            return False

    async def connect(self, message):
        ''' Connects Bot to voice channel if not in one
            Move to channel if in already in one
            Has an error check if self.voice is None but bot is still connected to voice
        '''

        # Check if user is in a voice channel to connect to
        if message.author.voice_channel is None:
            await self.bot.send_message(message.channel, "{0.mention}, You need to be in a voice channel I can connect to.".format(message.author))
        else:
            # Check is the bot is still connected to voice but not saved to self.voice
            if self.voice is None and self.bot.is_voice_connected(self.server):
                self.voice = self.bot.voice_client_in(self.server)
                if message.author.voice_channel is not self.voice.channel and self.checkMod(message.author):
                    await self.voice.move_to(message.author.voice_channel)
                    self.bot.log('warn', 'Voice still connected in {0.name} ({0.id}). Had to move channel after setting it back'.format(self.server))
                else:
                    self.bot.log('warn', 'Voice still connected in {0.name} ({0.id}). Setting voice back to that.'.format(self.server))
            else:
                # Check is user is allowed to connect bot (mod or not already connected)
                if self.checkMod(message.author) or self.voice is None:
                    # Check if bot is already connected
                    if self.bot.is_voice_connected(self.server):
                        # Check not already connected to that channel
                        if message.author.voice_channel is not self.voice.channel:
                            await self.voice.move_to(message.author.voice_channel)
                            self.text_channel = message.channel
                            await self.bot.send_message(message.channel, 'Connected to **{0}** and bound to this text channel'.format(message.author.voice_channel.name))
                        else:
                            await self.bot.send_message(message.channel, "{0.mention}, I'm already in your voice channel".format(message.author))
                    else:
                        # Connect to that voice channel
                        self.voice = await self.bot.join_voice_channel(message.author.voice_channel)
                        # Set text channel to the channel the message was sent in
                        self.text_channel = message.channel
                        await self.bot.send_message(message.channel, 'Connected to **{0}** and bound to this text channel'.format(message.author.voice_channel.name))
                else:
                    # Tell user they cannot move bot (as they can connect if bot is not already connected)
                    await self.bot.send_message(message.channel, 'Sorry {0.mention}, You need to be a mod to move me if someone else is listening to music'.format(message.author))

    async def disconnect(self, user, force=False, reloaded=False, crash=False):
        ''' Disconnect the bot from the voice channel (mod only)
            If no one is in the voice channel the bot forces the disconnect using force
            If a cog reload happens force and reload are used to tell the users using bot that a disconnect happened due to a reload
            This shouldn't happen unless the reload is really needed
            Return True if sucessful so the music player can be removed
        '''

        if force or self.checkMod(user):
            # Clear the queue
            self.queue = []
            # Skip current song
            if self.player is not None and not self.player.is_done():
                self.player.stop()
            # Disconnect voice
            if self.bot.is_voice_connected(self.server):
                await self.voice.disconnect()
            await asyncio.sleep(1)
            # Clear voice bot and player
            self.voice = None
            self.player = None
            if force:
                if crash:
                    return False
                elif reloaded:
                    await self.bot.send_message(self.text_channel, 'Disconnected due to a cog reload. Please wait a minute or two then reconnect me'.format(user))
                else:
                    await self.bot.send_message(self.text_channel, ':cry: Why did you all leave me? (Disconnected from voice)'.format(user))
                self.audio_player.cancel()
                return True
            else:
                await self.bot.send_message(self.text_channel, 'Disconnected from the voice channel by {0.display_name}'.format(user))
                self.audio_player.cancel()
                return True
        else:
            await self.bot.send_message(self.text_channel, 'Sorry {0.mention}, You need to be a mod to disconnect me'.format(user))
            return False

    async def crash(self,):
        ''' Reconnects the bot but keeps the queue so songs do not need to be added again. 
            While skipping the song that broke it
        '''

        # Make a copy of current queue 
        tempqueue = self.queue
        # Get the current voice channel
        channel = self.voice.channel
        # Log current song and server that people said crashed
        self.bot.log('warn', 'Apparent crash in {0.name} ({0.id}), with {1.title} ({1.url})'.format(self.server, self.player))
        # Disconnect
        await self.disconnect(self.bot.user, force=True, crash=True)
        # Reconnect
        self.voice = await self.bot.join_voice_channel(channel)
        # Put songs back in queue
        self.queue = tempqueue
        # Start playing again
        if self.player is None and len(self.queue) > 0:
            await self.bot.send_message(self.text_channel, "Reconnected. Will start playing the next song")
            self.songs_in_queue.set()
        else:
            await self.bot.send_message(self.text_channel, "Reconnected.")

    async def addQueue(self, message, link):
        ''' Adds link to the queue to be played
        '''

        valid = False
        start_pos = 1
        if self.voice is None:
            await self.bot.send_message(message.channel, '{0.mention}, I am not in a voice channel to play music. Please connect me first'.format(message.author))
        elif message.author.voice_channel != self.voice.channel:
            await self.bot.send_message(message.channel, '{0.mention}, You need to be in my voice channel to add a song'.format(message.author))
        else:
            # Check if link is youtube, soundcloud or a search
            search = False
            sc = False
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
                valid = True
                sc = False
            elif 'soundcloud.com' in link:
                # Soundcloud
                valid = True
                sc = True
            else:
                # Search
                if link.startswith('http://') or link.startswith('https://'):
                    valid = False
                    sc = False
                else:
                    valid = True
                    search = True
                    sc = False
            # If valid link or search
            if valid:
                # Download the info from the link
                # Set ytdl to use startpos and endpos to get info
                if search:
                    ytdl = youtube_dl.YoutubeDL({'default_search': 'auto' , 'simulate': True, 'skip_download': True, 'ignoreerrors': True, 'quiet': True})
                elif sc:
                    ytdl = youtube_dl.YoutubeDL({'playlistend': 20, 'playlistrandom': True, 'simulate': True, 'skip_download': True, 'ignoreerrors': True, 'quiet': True})
                else:
                    ytdl = youtube_dl.YoutubeDL({'playliststart': start_pos, 'playlistend': (start_pos + 19) , 'simulate': True, 'skip_download': True, 'ignoreerrors': True, 'quiet': True})
                # Send info message
                msg = 'Getting info from link. This might take a while please wait'
                temp_mesg = await self.bot.send_message(message.channel, msg)
                # Get info
                try:
                    result = ytdl.extract_info(link, download=False)
                except youtube_dl.utils.DownloadError as e:
                    # Invalid Link
                    if 'Incomplete YouTube ID' in str(e):
                        msg = '{0.mention}, Not a valid Youtube link'
                        await self.bot.edit_message(temp_mesg, msg.format(message.author))
                    elif 'Unable to download JSON metadata' in str(e):
                        msg = '{0.mention}, Not a valid Soundcloud link'
                        await self.bot.edit_message(temp_mesg, msg.format(message.author))
                else:
                    # Check if playlist was downloaded
                    if 'entries' in result:
                        queued = 0
                        for song in result['entries']:  
                            # Get song url, title and requester
                            if song is not None:
                                url = song['webpage_url']
                                title = song['title']
                                thumbnail = song['thumbnail']
                                user = message.author
                                # Add song to queue
                                self.queue.append(Song(url, title, thumbnail, user))
                                queued += 1
                            else:
                                self.bot.log('warn', "Video in {0}, could not be downloaded. Server: {1.name} ({1.id})".format(link, self.server))
                        # If search term added
                        if search:
                            msg = ':notes: Queued: **{0}**'
                            if self.time_left_paused is not None:
                                msg += ' Current song is *PAUSED*'
                            if result['entries'] is None:
                                await self.bot.edit_message(temp_mesg, "Video {0}, could not be downloaded".format(link))
                            else:
                                await self.bot.edit_message(temp_mesg, msg.format(result['entries'][0]['title']))
                        else:
                            if queued > 0:
                                # Tell the user how many songs have been queued                 
                                if sc:
                                    msg = 'Queued: **{0}** random songs [Videos in queue: {1}]'
                                else:
                                    msg = 'Queued: **{0}** songs [Videos in queue: {1}]'
                            else:
                                msg = 'No songs were added'
                            if self.time_left_paused is not None:
                                msg += ' Current song is *PAUSED*'
                            await self.bot.edit_message(temp_mesg, msg.format(str(queued), len(self.queue)))
                    else:
                        # Single song
                        # Get song url, title and requester
                        if result is not None:
                            url = result['webpage_url']
                            title = result['title']
                            thumbnail= result['thumbnail']
                            user = message.author                    
                            # Add song to queue
                            self.queue.append(Song(url, title, thumbnail, user))
                            # Tell the user the song has been queued
                            msg = ':notes: Queued: **{0}** [Videos in queue: {1}]'
                            if self.time_left_paused is not None:
                                msg += ' Current song is *PAUSED*'
                            await self.bot.edit_message(temp_mesg, msg.format(title, len(self.queue)))
                        else:
                            msg = 'Could not add that link to queue'
                            if self.time_left_paused is not None:
                                msg += ' Current song is *PAUSED*'
                            await self.bot.edit_message(temp_mesg, msg)
                            self.bot.log('warn', "Video from {1}, could not be downloaded. Server: {1.name} ({1.id})".format(link, self.server)) 
                # Start player is not already playing
                if len(self.queue) != 0:
                    self.songs_in_queue.set()
            else:
                await self.bot.send_message(message.channel, '{0.mention}, That was not a valid link or song search'.format(message.author))

    async def skip(self, message, force=False):
        ''' Start the vote skip or force if done by admin using force skip command
        '''

        # Check if there is a music player and it is playing
        if self.player != None and self.player.is_playing():
            # Check if forced
            if force:
                self.skips.clear()
                self.player.stop()
                await self.bot.send_message(message.channel, '**{0.display_name}** has forced skipped the song'.format(message.author))                
            else:
                if message.author.id not in self.skips:
                    self.skips.add(message.author.id)
                    total_votes = len(self.skips)
                    if total_votes >= 3:
                        self.skips.clear()
                        self.player.stop()
                        await self.bot.send_message(message.channel, '**{0.display_name}** has voted to skip.\nThe vote skip has passed.'.format(message.author))
                    else:
                        await self.bot.send_message(message.channel, '**{0.display_name}** has voted to skip [{1}/3].'.format(message.author, total_votes))
                else:
                    await self.bot.send_message(message.channel, '{0.mention}, You have already voted to skip'.format(message.author))

        else:
            # Send message saying there is nothing to skip
            await self.bot.send_message(message.channel, '{0.mention}, There is nothing playing to be skipped'.format(message.author))

    async def changeVolume(self, message, percent):
        ''' Change the volume of the bot
        '''

        if int(percent) < 0 or int(percent) > 200:
            # Send user error message for invalid percentage
            await self.bot.send_message(message.channel, '{0.mention}, Volume is done by percentage between 0%  and 200%, Please pick a vaild percentage'.format(message.author))
        else:
            # Change percentage to a valid number for ffmpeg or avconv
            self.volume = int(percent) / 100                        
            # Make sure there is a player to change the volume for
            if self.player is not None:
                self.player.volume = self.volume                        
            # Send volume has been changed message
            await self.bot.send_message(message.channel, '{0.mention}, Volume has been changed to: **{1}%**'.format(message.author, percent))

    async def pauseMusic(self, message):
        ''' Pauses the music 
        '''
        
        if self.player is not None:
            self.player.pause()
            self.time_left_paused = round(self.time_song_ends - time.time())
            await self.bot.send_message(message.channel, ':pause_button: **{0}** is now paused'.format(self.player.title))
        else:
            await self.bot.send_message(message.channel, '{0.mention}, There is nothing playing to be paused'.format(message.author))

    async def resumeMusic(self, message):
        ''' Resume the music 
        '''

        if self.player is not None:
            self.time_song_ends = time.time() + self.time_left_paused
            self.time_left_paused = None
            self.player.resume()
            await self.bot.send_message(message.channel, ':arrow_forward:  **{0}** is now playing'.format(self.player.title))
        else:
            await self.bot.send_message(message.channel, '{0.mention}, There is nothing paused'.format(message.author))

    async def clearQueue(self, message):
        ''' Clear the queue 
        '''
        
        self.queue = []
        await self.bot.send_message(message.channel, "{0.mention}, The queue has been cleared!!".format(message.author))

    async def nowPlaying(self, message):
        ''' Shows the current song that is playing and time left till next song
        '''

        # Nothing playing
        if self.current_song is None:
            await self.bot.send_message(message.channel, '{0.mention}, There is nothing playing'.format(message.author))
        else:
            # Get current duration if not paused
            if self.time_left_paused is None:
                time_left = round(self.time_song_ends - time.time())
                current_dur = self.player.duration - time_left
            else:
                # Get current duration if pasued
                current_dur = self.player.duration - self.time_left_paused
            # Split current duration in to hours, mins and seconds
            m, s = divmod(current_dur, 60)
            h, m = divmod(m, 60)
            # Do the same for complete duration
            fm, fs = divmod(self.player.duration, 60)
            fh, fm = divmod(fm, 60)
            # Based on how many hours there is in the song create embed
            if fh != 0:
                np = discord.Embed(type='rich', colour=discord.Colour(65280), description='**{0}** [{1:02d}:{2:02d}:{3:02d}/{4:02d}:{5:02d}:{6:02d}]'.format(self.player.title, h, m, s, fh, fm, fs))
            else:
                np = discord.Embed(type='rich', colour=discord.Colour(65280), description='**{0}** [{1:02d}:{2:02d}/{3:02d}:{4:02d}]'.format(self.player.title, m, s, fm, fs))
            # Change colour and author message based on if it paused or not
            if self.time_left_paused is not None:
                np.colour = discord.Colour(16711680)
                np.set_author(name='Now Playing [PAUSED]:', url=self.player.url)
            else:
                np.set_author(name='Now Playing:', url=self.player.url)
            # Put song requester in footer set thumbmail and send
            np.set_footer(text='Requested by {0}'.format(self.current_song.requester.display_name))
            np.set_thumbnail(url=self.current_song.thumbnail)
            await self.bot.send_message(message.channel, embed=np)

    async def showQueue(self, message):
        ''' Show the next few songs in the queue
        '''

        # If the only the current playing song or nothing is queue tell user
        if len(self.queue) == 0:
            await self.bot.send_message(message.channel, '{0.mention}, There are no songs in the queue'.format(message.author))
        else:
            if self.time_left_paused is None:
                # Get time left and spilt in hours, mins and seconds
                time_left = round(self.time_song_ends - time.time())
                m, s = divmod(time_left, 60)
                h, m = divmod(m, 60)
                # Based on how many hours there is in the song create embed
                desc = ''
                if h != 0:
                    qe = discord.Embed(type='rich', colour=discord.Colour(65535))
                    qe.set_author(name='Up Next:')
                    desc += '[{0[0].title}]({0[0].url}) - Requested by **{0[0].requester.display_name}**. Plays in {1:02d}:{2:02d}:{3:02d}s'.format(self.queue, h, m, s)
                else:
                    qe = discord.Embed(type='rich', colour=discord.Colour(65535))
                    qe.set_author(name='Up Next:')
                    desc += '[{0[0].title}]({0[0].url}) - Requested by **{0[0].requester.display_name}**. Plays in {1:02d}:{2:02d}:{3:02d}s'.format(self.queue, h, m, s)
            else:
                qe = discord.Embed(type='rich', colour=discord.Colour(65535))
                qe.set_author(name='Queue:')
                desc += '[{0[0].title}]({0[0].url}) - Requested by **{0[0].requester.display_name}**. Current song is *PAUSED*'.format(self.queue)
            
            # Check for more songs
            if len(self.queue) > 1:
                desc = '\nAfter:\n'
                if len(self.queue) < 6:
                    for i in range(1, len(self.queue)):
                        desc += '{0}: [{1[0].title}]({1[0].url}) - Requested by **{1[0].requester.display_name}**\n'.format(i, self.queue[i])
                else:
                    for i in range(1, 5):
                        desc += '{0}: [{1[0].title}]({1[0].url}) - Requested by **{1[0].requester.display_name}**\n'.format(i, self.queue[i])
                    # Display number of other songs
                    desc += 'And {0} more'.format(len(self.queue[6:]))

            qu.description = desc
            # Send embed
            await self.bot.send_message(message.channel, embed=qe)

class music:
    ''' Music player
        Create a server music player upon connect command which if music channel is forced
    '''

    def __init__(self, bot):
        self.bot = bot
        self.musicplayers = {}
        self.music_channels = {}
        self.loadFiles()

    async def _unload(self):
        ''' Unload function for when it is unloaded
        '''
        for server, player in self.musicplayers.copy().items():
            await player.disconnect(self.bot.user, force=True, reloaded=True)
            self.bot.log('info', 'Forcefully deleted {0} music player'.format(server))
            del self.musicplayers[server]

    def loadFiles(self):
        ''' Loads the files for the cog stored in cog data folder
        '''

        if not isdir('Flandre/data/music'):
            # Make the directory if missing and the files that go with it 
            self.bot.log('warn', 'Cogs data folder not found, it and all files have been made') 
            mkdir('Flandre/data/music')
            with open('Flandre/data/music/music_channels.json', 'w') as file:
                json.dump({}, file)   
        else:
            # Check for music_channels file
            try:
                with open('Flandre/data/music/music_channels.json', 'r') as file:
                    self.music_channels = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.music_channels = {}
                self.bot.log('error', 'music_channels.json could not be loaded. Reason: {0}'.format(e))                
                # Make the file for user again
                with open('Flandre/data/music/music_channels.json', 'w') as file:
                    json.dump({}, file)
                self.bot.log('info', 'Flandre/data/music/music_channels.json has been remade for you')

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def setmusicchannel(self, ctx):
        '''Sets the channel command is typed in as the music channel for that server
        '''

        removed = False
        if ctx.message.server.id in self.music_channels:
            self.music_channels.pop(ctx.message.server.id)
            removed = True
        else:
            self.music_channels[ctx.message.server.id] = ctx.message.channel.id
        
        try:
            with open('Flandre/data/music/music_channels.json', 'w') as file:
                json.dump(self.music_channels, file, indent=4, sort_keys=True)
        except:
            if removed:
                await self.bot.say('This channel is no longer the music channel for the server. However is couldn\'t be save for some reason')
            else:
                await self.bot.say('This channel has been made the music channel for the server. However is couldn\'t be save for some reason')
            self.bot.log('critical', 'Flandre/data/music/music_channels.json could not be saved. Please check it')
        else:
            if removed:
                await self.bot.say('This channel is no longer the music channel for the server.')
                self.bot.log('info', 'Flandre/data/music/music_channels.json has been saved. Reason: {0.name} ({0.id}) is no longer a logging channel'.format(ctx.message.channel))
            else:
                await self.bot.say('This channel has been made the music channel for the server.')
                self.bot.log('info', 'Flandre/data/music/music_channels.json has been saved. Reason: {0.name} ({0.id}) has been made a logging channel'.format(ctx.message.channel))

    @commands.command(pass_context=True, no_pm=True)
    async def connect(self, ctx):
        ''' Connects Bot to voice channel if not in one. Moves to channel if in already in one
        '''

        message = ctx.message
        if message.server.id not in self.music_channels:
            self.musicplayers[message.server.id] = MusicPlayer(self.bot, message.server)
            self.bot.log('info', 'Created Music Player for {0.name} ({0.id})'.format(message.server))
            await self.musicplayers[message.server.id].connect(message)
        else:
            if message.channel.id == self.music_channels[message.server.id]:
                self.musicplayers[message.server.id] = MusicPlayer(self.bot, message.server)
                self.bot.log('info', 'Created Music Player for {0.name} ({0.id})'.format(message.server))
                await self.musicplayers[message.server.id].connect(message)
            else:
                music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))

    @commands.command(pass_context=True, no_pm=True)
    async def disconnect(self, ctx):
        ''' Disconnect the bot from the voice channel (mod only)
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:            
                done = await self.musicplayers[message.server.id].disconnect(message.author)
                if done:
                    del self.musicplayers[message.server.id]
                    self.bot.log('info', 'Removed Music Player for {0.name} ({0.id})'.format(message.server))
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    done = await self.musicplayers[message.server.id].disconnect(message.author)
                    if done:
                        del self.musicplayers[message.server.id]
                        self.bot.log('info', 'Removed Music Player for {0.name} ({0.id})'.format(message.server))
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def crash(self, ctx):
        ''' Reconnects the bot but keeps the queue so songs do not need to be added again. 
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:            
                await self.musicplayers[message.server.id].crash()
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                     await self.musicplayers[message.server.id].crash()
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    async def add(self, ctx, link : str):
        ''' Add command <Youtube Link/Soundcloud Link/Search term>
        '''
        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].addQueue(message, link)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].addQueue(message, link)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):
        ''' Vote skip
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].skip(message)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].skip(message)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def forceskip(self, ctx):
        ''' Force skip
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].skip(message, force=True)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].skip(message, force=True)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True, aliases=["vol"])
    @permissions.checkMod()
    async def volume(self, ctx, percent : int):
        ''' Volume command <0 - 200 %>
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].changeVolume(message, percent)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].changeVolume(message, percent)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def pause(self, ctx):
        ''' Pause current song
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].pauseMusic(message)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].pauseMusic(message)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def resume(self, ctx):
        ''' Resume current song
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].resumeMusic(message)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].resumeMusic(message)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    @permissions.checkMod()
    async def clear(self, ctx):
        ''' Clear the queue
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].clearQueue(message)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].clearQueue(message)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(pass_context=True, no_pm=True)
    async def queue(self, ctx):
        ''' Show next few songs in the queue
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].showQueue(message)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].showQueue(message)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True, aliases=["np"])
    async def nowplaying(self, ctx):
        ''' Show current playing song 
        '''

        message = ctx.message
        if message.server.id in self.musicplayers:
            if message.server.id not in self.music_channels:
                await self.musicplayers[message.server.id].nowPlaying(message)
            else:
                if message.channel.id == self.music_channels[message.server.id]:
                    await self.musicplayers[message.server.id].nowPlaying(message)
                else:
                    music_channel = self.bot.get_channel(self.music_channels[message.server.id])
                    await self.bot.say('Music commands need to be done in {0.mention}'.format(music_channel))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    async def on_voice_state_update(self, before, after):
        ''' When voice channel update happens 
        '''
        server = after.server
        if self.bot.is_voice_connected(server) and after != self.bot.user:
            voice = self.bot.voice_client_in(server)
            channelmembers = voice.channel.voice_members
            # Do a check then wait 10 seconds if true
            if len(channelmembers) <= 1:
                await asyncio.sleep(10)
                # Do check again
                channelmembers = voice.channel.voice_members
                if len(channelmembers) <= 1:
                    if server.id in self.musicplayers:
                        done = await self.musicplayers[server.id].disconnect(self.bot.user, force=True)
                        if done:
                            if server.id in self.musicplayers:
                                del self.musicplayers[server.id]
                            self.bot.log('info', 'Removed Music Player for {0.name} ({0.id})'.format(server))

def setup(bot):
    n = music(bot)
    bot.add_listener(n.on_voice_state_update, "on_voice_state_update")
    bot.add_cog(n)