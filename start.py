''' start.py
Used to start the discord bot
Written by jackylam5 and maware 
'''
import Flandre
import sys

try:
    bot = Flandre.Bot()
except Flandre.MissingConfigFile:
    sys.exit()
else:
    try:
        bot.run()
    except Flandre.LoginError:
        sys.exit()
