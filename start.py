#!/usr/bin/env python3

''' start.py
Used to start the discord bot
Written by jackylam5 and maware
'''

import sys
import Flandre

if __name__ == '__main__':
    try:
        BOT = Flandre.Bot()
    except Flandre.MissingConfigFile:
        sys.exit()
    else:
        try:
            BOT.run()
        except Flandre.LoginError:
            sys.exit()
