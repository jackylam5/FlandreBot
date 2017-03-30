import discord
from discord.ext import commands
from os import mkdir
from os.path import isdir
from Flandre import permissions

class serverstuff:
    ''' Server Stuff cog holds welcome and leaving message for each server
        Also holds custom commands for each server
    '''

    def __init__(self, bot):
        self.bot = bot
        self.messages = {} # Each server have a dict with welcome/leaving and channel all are none if not wanted (server is removed if all is none)
        self.custom_commands = {}
        self.loadFiles()

    self loadFiles(self):
        ''' Loads the files for the cogs stored in the cogs data folder
        '''

        if not isdir('Flandre/data/serverstuff'):
            # Make the directory if missing and the files that go with it 
            self.bot.log('warn', 'Cogs data folder not found, it and all files have been made')
            mkdir('Flandre/data/serverstuff')
            with open('Flandre/data/serverstuff/messages.json', 'w') as file:
                json.dump({}, file)
            with open('Flandre/data/serverstuff/custom_commands.json', 'w') as file:
                json.dump({}, file)
        else:
            # Check for messages file and load it if there
            try:
                with open('Flandre/data/serverstuff/messages.json', 'r') as file:
                    self.messages = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.messages = {}
                self.bot.log('error', 'messages.json could not be loaded. Reason: {0}'.format(e))                
                # Make the file for user again
                with open('Flandre/data/serverstuff/messages.json', 'w') as file:
                    json.dump({}, file)
                self.bot.log('info', 'Flandre/data/serverstuff/messages.json has been remade for you')
            # Check for custom_command file and load it if there
            try:
                with open('Flandre/data/serverstuff/custom_commands.json', 'r') as file:
                    self.custom_commands = json.load(file)
            except (json.decoder.JSONDecodeError, IOError) as e:
                self.custom_commands = {}
                self.bot.log('error', 'custom_commands.json could not be loaded. Reason: {0}'.format(e))                
                # Make the file for user again
                with open('Flandre/data/serverstuff/custom_commands.json', 'w') as file:
                    json.dump({}, file)
                self.bot.log('info', 'Flandre/data/serverstuff/custom_commands.json has been remade for you')

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def setwelcomechannel(self, ctx):
        ''' Set the channel command is entered in as the channel for welcome and leaving messages
        '''

        message = ctx.message
        removed = False
        
        # Check if channel is to be removed
        if message.server.id in self.messages:
            if self.messages[message.server.id]['channel'] == message.channel.id:
                self.messages[message.server.id]['channel'] = None
                removed = True
            else:
                # do stuff
        else:
            #do stuff