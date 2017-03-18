import discord
from discord.ext import commands
import youtube-dl
import asyncio

class MusicPlayer:
	''' Music Player Class
		Manages connecting and disconnecting of the bot to that server
		Also manages adding and playing of songs
	'''

	def __init__(self, bot, server)
		# The bot and the sever this music player is for
		self.bot = bot
		self.server = server
		# Channel to post now playing to (default to the servers default channel)
        self.text_channel = server.default_channel
		# Voice connection and the actual player(youtube-dl)
		self.voice = None
		self.player = None
		# Player volume - 1 is 100% (Max: 2, Min: 0)
		self.volume = 0.15 
		# Queue will hold the song name, thumbnail for song, the url for that song and the name of the person that requested it in a dictionary
		self.queue = []
		# Duration used to get how long the song has left for show queue and now playing
		self.time_song_ends = None
        self.time_left_paused = None
        # Skipping current song
		self.skip_votes_needed = 0
		self.skip_votes = []

	def checkMod(self, user):
        ''' Check if user is mod needed as some admin commands can be used by non-admins
            if bot is not connected 
        '''
        
        if user.id in self.bot.config['ownerid']
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
            # Check if the player says there is no voice connection but the bot is still connected
			if self.voice is None and self.bot.is_voice_connected(self.server):
                # Log error and set self.voice to that connection 
                self.bot.log('warn', 'Voice still connected in {0.name} ({0.id}). Setting voice back to that.'.format(self.server))
                self.voice = self.bot.voice_client_in(self.server)                
                # Check user that connected bot is in different channel if so move there
                if message.author.voice_channel is not self.voice.channel:
                    self.bot.log('warn', 'Voice still connected in {0.name} ({0.id}). Had to move channel after setting it back'.format(self.server))
                    await self.voice.move_to(message.author.voice_channel)
			else:
                # Check is user is allowed to connect bot (mod or not already connected)
                if checkMod(message.author) or self.voice is None:
                    # Check if bot is already connected
                    if self.bot.is_voice_connected(self.server):
                        # Check not already connected to that channel
                        if message.author.voice_channel is not self.voice.channel:
                            await self.voice.move_to(message.author.voice_channel)
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

    async def disconnect(self, user, force=False, reload=False, crash=False):
        ''' Disconnect the bot from the voice channel (mod only)
            If no one is in the voice channel the bot forces the disconnect using force
            If a cog reload happens force and reload are used to tell the users using bot that a disconnect happened due to a reload
            This shouldn't happen unless the reload is really needed
            Return True if sucessful so the music player can be removed
        '''

        if force or checkMod(user):
            # Clear the queue
            self.queue = []
            # Skip current song
            if self.player != None:
                self.player.stop()
            self.skips_needed = 0
            self.votes = []
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
                return True
            else:
                await self.bot.send_message(self.text_channel, 'Disconnected from the voice channel by {0.display_name}'.format(user))
                return True
        else:
            await self.bot.send_message(self.text_channel, 'Sorry {0.mention}, You need to be a mod to disconnect me'.format(user))
            return False

    async def crash(self, user):
        ''' Reconnects the bot but keeps the queue so songs do not need to be added again. 
            While skipping the song that broke it
        '''

        # Make a copy of current queue minus current song
        tempqueue = self.queue[1:]
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
            await self.client.send_message(self.text_channel, "Reconnected. Will start playing the next song")
            await self.audioPlayer()
        else:
            await self.client.send_message(self.text_channel, "Reconnected.")

    async def audioPlayer(self):
        ''' Used to play the songs in the queue until queue is empty
        '''

        while True:
            # Check if queue is empty
            if len(self.queue) == 0:
                if self.player != None:
                    self.player.stop()
                self.player = None
                break
            else:
                # Stop the last song played
                if self.player is not None:
                    self.player.stop()
                # Play the audio

                try:
                    kwargs = {'use_avconv': False}
                    # Make youtube_dl download song
                    self.player = await self.voice.create_ytdl_player(url, ytdl_options={'quiet': True},**kwargs)
                    # Set volume
                    self.player.volume = self.volume
                except youtube_dl.utils.ExtractorError:
                    # Display error message is blocked
                    temp_msg = "Sorry {0} is blocked in my country"
                    await self.bot.send_message(self.text_channel, temp_msg.format(self.queue[0]['title']))
                except youtube_dl.utils.DownloadError:
                    # Display error message is blocked
                    temp_msg = "Sorry {0} is blocked in my country"
                    await self.bot.send_message(self.text_channel, temp_msg.format(self.queue[0]['title']))
                else:
                    # Get hours, mins and seconds
                    m, s = divmod(int(self.player.duration), 60)
                    h, m = divmod(m, 60)
                    # Create playing embed
                    np = discord.Embed(type='rich', colour=discord.Colour(65280), description='**{0}** ({1:02d}:{2:02d}:{3:02d}s)'.format(self.queue[0]['title'], h, m, s))
                    np.set_author(name='Now Playing:', url=self.queue[0]['url'])
                    np.set_footer(text='Requested by {0}'.format(self.queue[0]['user']))
                    np.set_thumbnail(url=self.queue[0]['thumbnail'])
                    # Send the now playing embed and start player
                    await self.bot.send_message(self.text_channel, embed=np)
                    await asyncio.sleep(1)
                    self.player.start()
                    self.song_end_time = time.time() + self.player.duration
                    # Sleep while music is playing and did not error
                    while self.player.is_playing() or not self.player.is_done():
                        if self.player.error is None:
                            await asyncio.sleep(1)
                        else:
                            self.bot.log('error', '{0.title} ({0.url}) has sent an error.'.format(self.player))
                            self.bot.log('error', 'Reason: {0}'.format(self.player.error))
                            await self.bot.send_message(self.text_channel, '{0.title} ({0.url}) has stopped due to an error (LOGGED). Playing next song!'.format(self.player))
                            break
                    # Clear the queue of that song and reset skip
                    self.skips_needed = 0
                    self.votes = []
                    if self.queue:
                        del self.queue[0]

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
            elif 'soundcloud.com' in link:
                # Soundcloud
                valid = True
            else:
                # Search
                if link.startswith('http://') or link.startswith('https://')
                    valid = False
                else:
                    valid = True
                    search = True
            # If valid link or search
            if valid:
                # Download the info from the link
                # Set ytdl to use startpos and endpos to get info
                if search:
                    ytdl = youtube_dl.YoutubeDL({'default_search': 'auto' , 'simulate': True, 'skip_download': True, 'ignoreerrors': True, 'quiet': True})
                else:
                    ytdl = youtube_dl.YoutubeDL({'playliststart': start_pos, 'playlistend': (start_pos + 9) , 'simulate': True, 'skip_download': True, 'ignoreerrors': True, 'quiet': True})
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
                                user = message.author.display_name
                                # Add song to queue
                                self.queue.append({'url': url, 'title': title, 'user': user, 'thumbnail': thumbnail})
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
                                msg = 'Queued: **{0}** songs'
                            else:
                                msg = 'No songs were added'
                            if self.pause_time_left is not None:
                                msg += ' Current song is *PAUSED*'
                            await self.bot.edit_message(temp_mesg, msg.format(str(queued)))
                    else:
                        # Single song
                        # Get song url, title and requester
                        if result is not None:
                            url = result['webpage_url']
                            title = result['title']
                            thumbnail= result['thumbnail']
                            user = message.author.display_name                    
                            # Add song to queue
                            self.queue.append({'url': url, 'title': title, 'user': user, 'thumbnail': thumbnail})
                            # Tell the user the song has been queued
                            msg = ':notes: Queued: **{0}**'
                            if self.pause_time_left is not None:
                                msg += ' Current song is *PAUSED*'
                            await self.bot.edit_message(temp_mesg, msg.format(title))
                        else:
                            msg = 'Could not add that link to queue'
                            if self.pause_time_left is not None:
                                msg += ' Current song is *PAUSED*'
                            await self.bot.edit_message(temp_mesg, msg)
                            self.bot.log('warn', "Video from {1}, could not be downloaded. Server: {1.name} ({1.id})".format(link, self.server)) 
                # Start player is not already playing
                if self.player is None and len(self.queue) > 0:
                    await self.audioPlayer()
            else:
                await self.bot.send_message(message.channel, '{0.mention}, That was not a valid link or song search')
                