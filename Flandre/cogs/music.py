import discord
from discord.ext import commands
import youtube_dl
import asyncio
import time
import json

# Music Player Class
class MusicPlayer():
    
    def __init__(self, bot, server):
        ''' Make all the variables for the music player '''
        
        # Bot and server for this music player
        self.bot = bot
        self.server = server
        # Voice connection and current player
        self.voice = None
        self.player = None
        self.volume = 0.25
        self.song_end_time = None
        self.pause_time_left = None
        # Queue will hold the song name, the url for that song and the name of the person that requested it in a dictionary
        self.queue = []
        self.repeat = False
        # Channel to post now playing to (default to the servers default channel)
        self.text_channel = server.default_channel
        # Skip (if active/current voters that have voted to skip)
        self.skips_needed = 0
        self.votes = []
        # Config files
        self.config = {}
        self.loadConfig()

    def checkAdmin(self, user):
        ''' Check if the user is an admin (Has manage server permission) on the server '''
                
        return user.permissions_in(self.text_channel).manage_server  
        
    def checkApproved(self, user):
        ''' Check is the user is in the list of approved users '''
        
        return (user.id == self.config['ownerid'])
        
        
    def loadConfig(self):
        ''' Load the config from the config.json file '''
        try:
            with open('FlandreBot/config.json', 'r') as config:
                self.config = json.load(config)
        except json.decoder.JSONDecodeError:
            pass    
    
    async def connect(self, message):
        ''' Connect the bot to the voice channel '''
        
        #Check if member is in a voice channel to conect to
        if message.author.voice_channel is None:
            await self.bot.send_message(message.channel, "{0.mention}, You need to be in a voice channel for me to connect to".format(message.author))
        else: 
            if self.voice is None and self.bot.is_voice_connected(self.server):
                self.bot.logger.warning("Voice still connected in {0.name} ({0.id}). Setting voice back to that.".format(self.server))
                self.voice = self.bot.voice_client_in(self.server)
            else:
                if self.checkAdmin(message.author) or self.checkApproved(message.author) or self.voice == None:
                    # If already connected
                    if self.bot.is_voice_connected(self.server):
                        # Move to that channel
                        await self.voice.move_to(message.author.voice_channel)
                    else:
                        # Connected to a channel in that server
                        self.voice = await self.bot.join_voice_channel(message.author.voice_channel)
                
                    # Set text channel to the channel the message was sent in
                    self.text_channel = message.channel
                    await self.bot.send_message(message.channel, 'Binding to this text channel and playing in **{0}**'.format(message.author.voice_channel.name))
                else:
                    await self.bot.send_message(message.channel, 'Sorry {0.mention}, You need to have the manage server permission or be approved to move me into a new channel while I am singing an song'.format(message.author))

    async def disconnect(self, user, force=False, reloaded=False):
        ''' Disconnect the bot from a voice channel '''
            
        if force or self.checkAdmin(user) or self.checkApproved(user):
            # Clear queue
            self.queue = []
            self.repeat = False

            # Skip current song
            if self.player != None:
                self.player.stop()
            self.skips_needed = 0
            self.votes = []

            # Disconnect voice
            if self.bot.is_voice_connected(self.server):
                await self.voice.disconnect()

            await asyncio.sleep(2)
            # Clear voice bot and player
            self.voice = None
            self.player = None

            if force:
                if reloaded:
                    await self.bot.send_message(self.text_channel, 'Disconnected due to a cog reload. Please wait a minute or two then reconnect me'.format(user))
                else:
                    await self.bot.send_message(self.text_channel, ':cry: Why did you all leave me? (Disconnected from voice)'.format(user))
            else:
                await self.bot.send_message(self.text_channel, 'Disconnected from the voice channel by {0.display_name}'.format(user))
                return 1
        else:
            await self.bot.send_message(self.text_channel, 'Sorry {0.mention}, You need to have the manage server permission or be approved to use this command!'.format(user))
            return None

    async def playLink(self, url):
        ''' Play the url given and set the volume '''
        
        # Set arguments for avconv 
        kwargs = {'use_avconv': False}
        # Make youtube_dl download song
        self.player = await self.voice.create_ytdl_player(url, ytdl_options={'quiet': True},**kwargs)
        # Set volume
        self.player.volume = self.volume

    async def changeVolume(self, message):
        ''' Function to change the volume of the bot '''
        
        if self.checkAdmin(message.author) or self.checkApproved(message.author):
            # Remove the command from the message
            try:
                percentage = message.content.split(' ', 1)[1]
            except IndexError:
                await self.bot.send_message(message.channel, '{0.mention}, No arguments given'.format(message.author))
            else:
                # Check if argument given is an integer
                if percentage.isdigit():
                    if int(percentage) < 0 or int(percentage) > 200:
                        # Send user error message for invalid percentage
                        await self.bot.send_message(message.channel, '{0.mention}, Volume is done by percentage between 0%  and 200%, Please pick a vaild percentage'.format(message.author))
                    else:
                        # Change percentage to a valid number for ffmpeg or avconv
                        self.volume = int(percentage) / 100
                        
                        # Make sure there is a player to change the volume for
                        if self.player is not None:
                            self.player.volume = self.volume
                        
                        # Send volume has been changed message
                        await self.bot.send_message(message.channel, '{0.mention}, Volume has been changed to: **{1}%**'.format(message.author, percentage))
                else:
                    await self.bot.send_message(message.channel, '{0.mention}, The arguments for this command has to be a integer'.format(message.author))
        else:
            await self.bot.send_message(message.channel, 'Sorry {0.mention}, You need to have the manage server permission or be approved to use this command!'.format(message.author))

    async def skip(self, message):
        ''' Start vote to skip/manage the vote or force skip if done by an admin '''
        
        # Check for arguments
        try:
            args = message.content.split(' ', 1)[1]
        except IndexError:
            args = ''

        
        # Check if forced and user is admin or approved
        if args == '-f' and (self.checkAdmin(message.author) or self.checkApproved(message.author)):
            # Check if there is a music player and it is playing
            if self.player != None and self.player.is_playing():
                # Skip
                self.player.stop()
                await self.bot.send_message(message.channel, '**{0.display_name}** has forced skipped the song'.format(message.author))
                # Reset skip
                self.skips_needed = 0
                self.votes = []
            else:
                # Send message saying there is nothing to skip
                await self.bot.send_message(message.channel, '{0.mention}, There is nothing playing to be skipped'.format(message.author))
        else:
            # If there is a music player and it is playing
            if self.player != None and self.player.is_playing():
                if message.author.id in self.votes:
                    await self.bot.send_message(message.channel, '{0.mention}, You have already voted to skip'.format(message.author))
                else:
                    # First vote skip
                    if not self.votes:
                        numofmembers = len(self.voice.channel.voice_members)
                        self.skips_needed = int(numofmembers*0.6)

                    # Add users to voted list
                    self.votes.append(message.author.id)

                    # Check if max has been reached
                    if len(self.votes) == self.skips_needed:
                        await self.bot.send_message(message.channel, '**{0.display_name}** has voted to skip.\nThe vote skip has passed.'.format(message.author))
                        # Skip
                        self.player.stop()
                        # Reset skip
                        self.skips_needed = 0
                        self.votes = []
                    else:
                        # Say remaning votes left
                        votes_needed_left = self.skips_needed - len(self.votes)
                        await self.bot.send_message(message.channel, '**{0.display_name}** has voted to skip.\n**{1}** more votes needed to skip.'.format(message.author, votes_needed_left))
            else:
                # Send message saying there is nothing to skip
                await self.bot.send_message(message.channel, '{0.mention}, There is nothing playing to be skipped'.format(message.author))

    async def addQueue(self, message): 
        ''' Add songs to the queue to be played '''

        queue_len = len(self.queue)
        start_pos = 1

        # Check if user is in the samer voice channel as the bot
        if self.voice is None:
            await self.bot.send_message(message.channel, '{0.mention}, I am not in a voice channel to play music. Get an admin or approved user do use the connect command'.format(message.author))
        elif message.author.voice_channel != self.voice.channel:
            await self.bot.send_message(message.channel, '{0.mention}, You need to be in my voice channel to add a song'.format(message.author))
        else:
            # Check for arguments
            try:
                link = message.content.split(' ', 1)[1]
            except IndexError:
                await self.bot.send_message(message.channel, '{0.mention}, You need to enter a Youtube or SoundCloud link for me to play'.format(message.author))
            else:
                search = False
                # Check for youtube video
                if 'youtube.com' in link or 'youtu.be' in link:
                    if 'youtu.be' in link:
                        vidID = link.split('/')[-1]
                        link = 'https://www.youtube.com/watch?v=' + vidID

                    if '&index' in link:
                        temp = link.split('&')
                        for i in range(0, len(temp)):
                            if 'index=' in temp[i]:
                                # Get start pos and end pos
                                start_pos = int(temp[i].replace('index=', '').strip())
                                break
                
                elif 'soundcloud.com' not in link:
                    search = True

                # Download the info from the link
                # Set ytdl to use startpos and endpos to get info
                if search:
                    ytdl = youtube_dl.YoutubeDL({'default_search': 'auto' , 'simulate': True, 'skip_download': True, 'ignoreerrors': True, 'quiet': True})
                else:
                    ytdl = youtube_dl.YoutubeDL({'playliststart': start_pos, 'playlistend': (start_pos + 24) , 'simulate': True, 'skip_download': True, 'ignoreerrors': True, 'quiet': True})
                # Send info message
                msg = 'Getting info from link. This might take a while please wait'
                temp_mesg = await self.bot.send_message(message.channel, msg.format(message))

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
                                # Make sure the video title cannot break code box in message
                                if '`' in title:
                                    title = title.replace('`', '\'')
                                # Add song to queue
                                self.queue.append({'url': url, 'title': title, 'user': user, 'thumbnail': thumbnail})
                                queued += 1
                            else:
                                self.bot.logger.warning("Video in {0}, could not be downloaded".format(link))

                        if search:
                            msg = ':notes: Queued: **{0}**'
                            if self.pause_time_left is not None:
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
                        # Get song url, title and requester
                        if result is not None:
                            url = result['webpage_url']
                            title = result['title']
                            thumbnail= result['thumbnail']
                            user = message.author.display_name
                            # Make sure the video title cannot break code box in message
                            if '`' in title:
                                title = title.replace('`', '\'')
                            # Add isong to queue
                            self.queue.append({'url': url, 'title': title, 'user': user, 'thumbnail': thumbnail})

                            # Tell the user the song has been queue
                            msg = ':notes: Queued: **{0}**'
                            if self.pause_time_left is not None:
                                msg += ' Current song is *PAUSED*'

                            await self.bot.edit_message(temp_mesg, msg.format(title))
                        else:
                            msg = 'Could not add that song'
                            if self.pause_time_left is not None:
                                msg += ' Current song is *PAUSED*'
                            await self.bot.edit_message(temp_mesg, msg)
                            self.bot.logger.warning("[{0.name}] Video from {1}, could not be downloaded".format(self.server, link))

                if self.player is None and len(self.queue) > 0:
                    await self.audioPlayer()

    async def audioPlayer(self):
        ''' Function that plays the songs in the queue '''

        while True:
            # Check if the queue is empty
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
                    await self.playLink(self.queue[0]['url'])
                except youtube_dl.utils.ExtractorError:
                    # Display error message is blocked
                    temp_msg = "Sorry {0} is blocked in my country"
                    await self.bot.send_message(self.text_channel, temp_msg.format(self.queue[0]['title']))
                except youtube_dl.utils.DownloadError:
                    # Display error message is blocked
                    temp_msg = "Sorry {0} is blocked in my country"
                    await self.bot.send_message(self.text_channel, temp_msg.format(self.queue[0]['title']))
                else:
                    # Get mins and seconds
                    m, s = divmod(int(self.player.duration), 60)
                    h, m = divmod(m, 60)                    
                
                    np = discord.Embed(type='rich', colour=discord.Colour(65280), description='**{0}** ({1:02d}:{2:02d}:{3:02d}s)'.format(self.queue[0]['title'], h, m, s))
                    np.set_author(name='Now Playing:', url=self.queue[0]['url'])
                    np.set_footer(text='Requested by {0}'.format(self.queue[0]['user']))
                    np.set_thumbnail(url=self.queue[0]['thumbnail'])
                    # Send the current playing title + duration and who requested it and start audio
                    await self.bot.send_message(self.text_channel, embed=np)
                    await asyncio.sleep(1)
                    self.player.start()
                    self.song_end_time = time.time() + self.player.duration

                    # Sleep while music is playing
                    while self.player.is_playing() or not self.player.is_done():
                        await asyncio.sleep(1)

                    # Clear the queue of that song and reset skip
                    self.skips_needed = 0
                    self.votes = []
                    if self.queue and not self.repeat:
                        del self.queue[0]

    async def nowPlaying(self, message):
        if len(self.queue) == 0:
            msg = '{0.mention}, There is nothing playing'
            await self.bot.send_message(message.channel, msg.format(message.author))
        else:
            if self.pause_time_left is None:
                time_left = round(self.song_end_time - time.time())
                current_dur = self.player.duration - time_left
            else:
                #time_left = round(self.player.duration - self.pause_time_left)
                current_dur = self.player.duration - self.pause_time_left
            
            # split current_dir int h,m,s
            m, s = divmod(current_dur, 60)
            h, m = divmod(m, 60)

            # split duration into h,m,s
            dm, ds = divmod(self.player.duration, 60)
            dh, dm = divmod(dm, 60)
            
            if dh != 0:
                np = discord.Embed(type='rich', colour=discord.Colour(65280), description='**{0}** [{1:02d}:{2:02d}:{3:02d}/{4:02d}:{5:02d}:{6:02d}]'.format(self.player.title, h, m, s, dh, dm, ds))
                msg = "{0.mention}, :arrow_forward: The current song is **{1} [{2:02d}:{3:02d}:{4:02d}/{5:02d}:{6:02d}:{7:02d}]**"
            else:
                np = discord.Embed(type='rich', colour=discord.Colour(65280), description='**{0}** [{2:02d}:{3:02d}/{5:02d}:{6:02d}]'.format(self.player.title, h, m, s, dh, dm, ds))

            if self.pause_time_left is not None:
                np.colour = discord.Colour(16711680)
                np.set_author(name='Now Playing [PAUSED]:', url=self.queue[0]['url'])
            else:
                np.set_author(name='Now Playing:', url=self.queue[0]['url'])            
            
            np.set_footer(text='Requested by {0}'.format(self.queue[0]['user']))
            np.set_thumbnail(url=self.queue[0]['thumbnail'])
            await self.bot.send_message(message.channel, embed=np)

    async def showQueue(self, message):
        ''' Show the songs that will be played next '''

        if len(self.queue) < 2:
            await self.bot.send_message(message.channel, '{0.mention}, There are no songs in the queue'.format(message.author))
        elif len(self.queue) == 2:
            if self.pause_time_left is None:
                time_left = round(self.song_end_time - time.time())
                m, s = divmod(time_left, 60)
                h, m = divmod(m, 60)

                if h != 0:
                    msg = "{0.mention}, The next song is **{1[1][title]}** and it was requested by **{1[1][user]}**. Plays in {2:02d}:{3:02d}:{4:02d}s"
                else:
                    msg = "{0.mention}, The next song is **{1[1][title]}** and it was requested by **{1[1][user]}**. Plays in {3:02d}:{4:02d}s"
                await self.bot.send_message(message.channel, msg.format(message.author, self.queue, h, m, s))
            else:
                msg = "{0.mention}, The next song is **{1[1][title]}** and it was requested by **{1[1][user]}**. Current song is *PAUSED*"
                await self.bot.send_message(message.channel, msg.format(message.author, self.queue))

        else:
            if self.pause_time_left is None:
                    time_left = round(self.song_end_time - time.time())
                    m, s = divmod(time_left, 60)
                    h, m = divmod(m, 60)
                    
                    if h != 0:
                        msg = "{0.mention}, The next song is **{1[1][title]}** and it was requested by **{1[1][user]}**. Plays in {2:02d}:{3:02d}:{4:02d}s\nQueue:\n```"
                    else:
                        msg = "{0.mention}, The next song is **{1[1][title]}** and it was requested by **{1[1][user]}**. Plays in {3:02d}:{4:02d}s\nQueue:\n```"
            else:
                msg = "{0.mention}, The next song is **{1[1][title]}** and it was requested by **{1[1][user]}**. Current song is *PAUSED*\nQueue:\n```"
            
            if len(self.queue) < 7:
                for i in range(2, len(self.queue)):
                    msg = msg + str((i-1)) + ": " + self.queue[i]['title'] + " - Requested by " + self.queue[i]['user'] + "\n"
            else:
                for i in range(2, 6):
                    msg = msg + str((i-1)) + ": " + self.queue[i]['title'] + " - Requested by " + self.queue[i]['user'] + "\n"

            msg = msg + '```'
            if self.pause_time_left is None:
                await self.bot.send_message(message.channel, msg.format(message.author, self.queue, h, m, s))
            else:
                await self.bot.send_message(message.channel, msg.format(message.author, self.queue))

    async def clearQueue(self, message):
        ''' Clear the queue '''
        if self.checkAdmin(message.author) or self.checkApproved(message.author):
            del(self.queue[1:])
            await self.bot.send_message(message.channel, "{0.mention}, The queue has been cleared!!".format(message.author))
        else:
            await self.bot.send_message(message.channel, 'Sorry {0.mention}, You need to have the manage server permission or be approved to use this command!'.format(message.author))

    async def pauseMusic(self, message):
        ''' Pauses the music '''
        
        if self.checkAdmin(message.author) or self.checkApproved(message.author):
            if self.player is not None:
                self.player.pause()
                self.pause_time_left = round(self.song_end_time - time.time())
                await self.bot.send_message(message.channel, ':pause_button: **{0}** is now paused'.format(self.player.title))
            else:
                await self.bot.send_message(message.channel, '{0.mention}, There is nothing playing to be paused'.format(message.author))
        else:
            await self.bot.send_message(message.channel, 'Sorry {0.mention}, You need to have the manage server permission or be approved to use this command!'.format(message.author))

    async def resumeMusic(self, message):
        ''' Resume the music '''

        if self.checkAdmin(message.author) or self.checkApproved(message.author):
            if self.player is not None:
                self.song_end_time = time.time() + self.pause_time_left
                self.pause_time_left = None
                self.player.resume()
                await self.bot.send_message(message.channel, ':arrow_forward:  **{0}** is now playing'.format(self.player.title))
            else:
                await self.bot.send_message(message.channel, '{0.mention}, There is nothing paused'.format(message.author))
        else:
            await self.bot.send_message(message.channel, 'Sorry {0.mention}, You need to have the manage server permission or be approved to use this command!'.format(message.author))

# Music cog
class music():
    ''' Music player written by maware for jacky <3
    Create a server music player upon connect command which must be done in a channel with music in it's name
    '''
    def __init__(self, bot):
        self.bot = bot
        self.musicplayers = {}
        

    # unload function for when it is unloaded
    async def _unload(self):
        for server, player in self.musicplayers.copy().items():
            await player.disconnect(self.bot.user, force=True, reloaded=True)
            self.bot.logger.info('Forcefully deleted {0} music player'.format(server))
            del self.musicplayers[server]

    @commands.command(no_pm=True, pass_context=True)
    async def connect(self, ctx):
        ''' Connect command '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        if message.server.id not in self.musicplayers:
            self.musicplayers[message.server.id] = MusicPlayer(self.bot, message.server)
            self.bot.logger.info('Created Music Player for {0.name} ({0.id})'.format(message.server))
            await self.musicplayers[message.server.id].connect(message)
            

    @commands.command(no_pm=True, pass_context=True)
    async def disconnect(self, ctx):
        ''' Disconnect Command '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].disconnect(message.author)
            del self.musicplayers[message.server.id]
            self.bot.logger.info('Removed Music Player for {0.name} ({0.id})'.format(message.server))
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def volume(self, ctx):
        ''' Volume command <0 - 200 %>'''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].changeVolume(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))  
                
    @commands.command(no_pm=True, pass_context=True)
    async def skip(self, ctx):
        ''' Skip Command <-f> to force if server admin'''
        
        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].skip(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def add(self, ctx):
        ''' Add command <Youtube Link/Soundcloud Link/Search term>'''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].addQueue(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def nowplaying(self, ctx):
        ''' Now Playing command '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].nowPlaying(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def np(self, ctx):
        ''' Now Playing command alias '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].nowPlaying(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def queue(self, ctx):
        ''' Queue Command '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].showQueue(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def clear(self, ctx):
        ''' Clear Command '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].clearQueue(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def pause(self, ctx):
        ''' Pause Command '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].pauseMusic(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    @commands.command(no_pm=True, pass_context=True)
    async def resume(self, ctx):
        ''' Resume Command '''

        message = ctx.message
        if not 'music' in message.channel.name.lower():
            await self.bot.send_message(message.channel, 'Music text channel command only')
            return
        # Check if there is a music player
        if message.server.id in self.musicplayers:
            await self.musicplayers[message.server.id].resumeMusic(message)
        else:
            await self.bot.send_message(message.channel, "{0.mention}, I am currently not connected to a voice channel".format(message.author))

    async def on_voice_state_update(self, before, after):
        ''' When voice channel update happens '''
        server = after.server
        if self.bot.is_voice_connected(server):
            voice = self.bot.voice_client_in(server)
            channelmembers = voice.channel.voice_members
            if len(channelmembers) <= 1:
                if server.id in self.musicplayers:
                    await self.musicplayers[server.id].disconnect(self.bot.user, force=True)
                    del self.musicplayers[server.id]
                    self.bot.logger.info('Removed Music Player for {0.name} ({0.id})'.format(server))
    
            
def setup(bot):
    n = music(bot)
    bot.add_listener(n.on_voice_state_update, "on_voice_state_update")
    bot.add_cog(n)