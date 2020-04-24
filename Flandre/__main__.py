#!/usr/bin/env python3

''' start.py
Used to start the discord bot
Written by jackylam5 and maware
'''

import sys
from . import core

if __name__ == '__main__':
    try:
        BOT = core.Bot()
    except core.MissingConfigFile:
        sys.exit()
    else:
        try:
            BOT.run()
        except core.LoginError:
            sys.exit()
