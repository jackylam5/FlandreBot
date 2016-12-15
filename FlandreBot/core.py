'''
Core Bot file
Handles all discord events such as:
	- Message received
	- Bot joins a server
	- Member joins a server
'''
import discord
from discord.ext import commands


class BOT(commands.Bot):

	def __init__(self, prefix, description):
		super().__init__(command_prefix = prefix, description = description)

	async def on_ready(self):
		''' When bot has fully logged on '''
		print('[*] Logged in as: {0.user.name} ({0.user.id})'.format(self))
		self.load_extension('FlandreBot.cogs.Owner')
		self.load_extension('FlandreBot.cogs.test')
		
