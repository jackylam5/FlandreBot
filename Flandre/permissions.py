from discord.ext import commands
import json

def checkOwners():
    ''' Check if user in in the config file as a owner
    '''
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

    return commands.check(checkOwnerPerm)
