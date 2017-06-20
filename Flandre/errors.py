''' error.py
Written by jackylam5 & maware
Holds all the custom errors
'''
from discord.ext import commands

class MissingConfigFile(Exception):
    ''' The error raised if the config file is missing '''
    pass

class LoginError(Exception):
    ''' The error raised if token is missing from config '''
    pass

class CogDisabled(commands.CommandError):
    ''' The cog has been disabled '''
    pass