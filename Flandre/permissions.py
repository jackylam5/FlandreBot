import discord
from discord.ext import commands
import json

def checkOwnerPerm(ctx):
    try:
        with open(f'{__package__}/config.json', 'r') as config:
            config = json.load(config)
    except:
        return False
    else:
        if author.id in config['ownerid']:
            return True
        else:
            return False

def checkAdminPerm(ctx):
    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False
    return ctx.channel.permissions_for(ctx.author).manage_guild

def checkModPerm(ctx):
    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False
    return ctx.channel.permissions_for(ctx.author).manage_channels

def checkOwners():
    ''' Check if user in in the config file as a owner
    '''

    return commands.check(checkOwnerPerm)

def checkAdmin():
    ''' Check if user is admin or higher
    '''
    def checkperm(ctx):
    
        if checkOwnerPerm(ctx):
            return True
        elif checkAdminPerm(ctx):
            return True
        else:
            return False

    return commands.check(checkperm)

def checkMod():
    def checkperm(ctx):
    
        if checkOwnerPerm(ctx):
            return True
        elif checkAdminPerm(ctx):
            return True
        elif checkModPerm(ctx):
            return True
        else:
            return False

    return commands.check(checkperm)
