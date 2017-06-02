''' permissions.py
Holds custom decorators to check permissioms for commands
'''
import json

import discord
from discord.ext import commands


def check_owner_perm(ctx):
    '''Check if user is a owner of the bot from config'''
    try:
        with open(f'{__package__}/config.json', 'r') as file:
            config = json.load(file)
    except:
        return False
    else:
        if ctx.author.id in config['ownerid']:
            return True
        else:
            return False

def check_admin_perm(ctx):
    '''Used to check is user has the manage_guild permission'''
    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False
    return ctx.channel.permissions_for(ctx.author).manage_guild

def check_mod_perm(ctx):
    '''Used to check is user has the manage_channels permission'''
    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False
    return ctx.channel.permissions_for(ctx.author).manage_channels

def check_owners():
    ''' Check if user is a owner
    '''

    return commands.check(check_owner_perm)

def check_admin():
    ''' Check if user is admin or higher '''
    def checkperm(ctx):
        ''' Check the different perms '''
        if check_owner_perm(ctx):
            return True
        elif check_admin_perm(ctx):
            return True
        else:
            return False

    return commands.check(checkperm)

def check_mod():
    ''' Check if user is admin or higher '''
    def checkperm(ctx):
        ''' Check the different perms '''
        if check_owner_perm(ctx):
            return True
        elif check_admin_perm(ctx):
            return True
        elif check_mod_perm(ctx):
            return True
        else:
            return False

    return commands.check(checkperm)
