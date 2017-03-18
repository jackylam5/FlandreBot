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

	async def connect(self, message):
		''' Connects Bot to voice channel if not in one
			Move to channel if in already in one
			Has an error check if self.voice is None but bot is still connected to voice
		'''

		# Check if user is in a voice channel to connect to
		if message.author.voice_channel is None:
			await self.bot.send_message(message.channel, "{0.mention}, You have to be in a voice channel for me to connect to when you use this comand".format(message.author))
		else:
			# Check if the player says there is no voice connection but the bot is still connected
			if self.voice is None and self.bot.is_voice_connected(self.server):
				