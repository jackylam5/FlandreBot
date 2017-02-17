from discord.ext import commands
import json

def checkOwnerPerm(ctx):
    user = ctx.message.author
    ''' Check is the user is in the list of approved users '''
    try:
        with open('Flandre/config.json', 'r') as config:
            config = json.load(config)
            if user.id in config['ownerid']:
                return True
            else:
                return False
    except json.decoder.JSONDecodeError:
        return False  

def checkOwner():
    return commands.check(checkOwnerPerm)


def checkAdminPerm(ctx):
    user = ctx.message.author
    channel = ctx.message.channel
    if channel.is_private:
        return False
    ''' Check if the user is an admin (Has manage server permission) on the server '''
    return user.permissions_in(channel).manage_server  
    
def checkAdmin():

    def checkperm(ctx):
    
        if checkOwnerPerm(ctx):
            return True
        if checkAdminPerm(ctx):
            return True
        return False

    return commands.check(checkperm)
    
def checkModPerm(ctx):
    user = ctx.message.author
    channel = ctx.message.channel
    ''' Check if the user is an mod (Has manage channels permission) on the server '''
    return user.permissions_in(channel).manage_channels
    
def checkMod():
    def checkperm(ctx):
    
        if checkOwnerPerm(ctx):
            return True
        if checkAdminPerm(ctx):
            return True
        if checkModPerm(ctx):
            return True
        return False

    return commands.check(checkperm)
        

    