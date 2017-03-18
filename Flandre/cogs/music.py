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

