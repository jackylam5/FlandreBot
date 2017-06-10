''' start.py
Used to start the discord bot
Written by jackylam5 and maware
'''

import sys
import Flandre

try:
    BOT = Flandre.Bot()
except Flandre.MissingConfigFile:
    sys.exit()
else:
    try:
        BOT.run()
    except Flandre.LoginError:
        sys.exit()
