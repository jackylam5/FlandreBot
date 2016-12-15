import FlandreBot
import discord
import asyncio
import time
import os


# Make the Bot always run
run = True
while run:
	# Make new Bot and get asyncio loop
	try:
		loop = asyncio.get_event_loop()
		bot = FlandreBot.BOT(prefix = '!', description = 'test')
	except Exception as e:
		print('[!] Error: {0}'.format(e))
		run = False	
	else:		
		try:
			# Start bot
			loop.run_until_complete(bot.start('MjQ3NDAzNTM5MTg4NTQ3NTg0.CzP8PQ.OyTUSzCBXtXQ25KNbbhtrLi_uII'))
		except discord.LoginFailure:
			# Logon Fails
			loop.run_until_complete(bot.logout())
			print('--------------------------------------')
			print('Invalid credentials')
			print('Please check token and re-run script')
			run = False
		except discord.ClientException:
			# Client Crashes
			loop.run_until_complete(bot.logout())
			print('--------------------------------------')
			print('Disconnected')
			print('Will try to reconnect after 20 seconds')
			time.sleep(20)
			run = True
		except discord.DiscordException:
			# Discord disconnected the Bot
			loop.run_until_complete(bot.logout())
			print('--------------------------------------')
			print('Disconnected')
			print('Will try to reconnect after 20 seconds')
			time.sleep(20)
			run = True
		except ConnectionResetError:
			# Web Conection Reset
			loop.run_until_complete(bot.logout())
			print('--------------------------------------')
			print('Disconnected')
			print('Will try to reconnect after 20 seconds')
			time.sleep(20)
			run = True
		except KeyboardInterrupt:
			# Keyboard Interrupt
			loop.run_until_complete(bot.logout())
			print('--------------------------------------')
			print('Disconnected')
			run = False
		finally:
			if run == False:
				loop.close()