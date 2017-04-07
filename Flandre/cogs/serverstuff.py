import discord
from discord.ext import commands
from os import mkdir
from os.path import isdir
from Flandre import permissions
import json
import asyncio

class serverstuff:
    ''' Server Stuff cog holds welcome and leaving message for each server
        Also holds custom commands for each server
    '''

    def __init__(self, bot):
        self.bot = bot
        self.messages = {} # Each server have a dict with welcome/leaving and channel all are none if not wanted (server is removed if all is none)
        self.custom_commands = {}
        self.loadFiles()

    def loadFiles(self):
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

    def saveServerMessages(self):
        ''' Save the server messages to json file
        '''

        with open('Flandre/data/serverstuff/messages.json', 'w') as file:
            json.dump(self.messages, file)
        self.bot.log('info', 'messages.json has been saved due to change.')

    def checkServerMessages(self, server):
        ''' Check if the server has both welcome and leaving as None if so ther server is removed from the list
        '''

        server_messages = self.messages[server.id]
        if server_messages['welcome'] is None and server_messages['leave'] is None:
            del self.messages[server.id]
            self.bot.log('info', '{0.name} ({0.id}) has removed server messages'.format(server))

    def addServerMessages(self, server):
        ''' Add the server to the server messages with default messages
        '''
        
        self.messages[server.id] = {'channel': None, 'welcome': 'Welcome %user% to %server%. Enjoy your stay!', 'leave': '%user% has left the server!'}
        self.bot.log('info', '{0.name} ({0.id}) has added server messages'.format(server))

    def saveServerCommands(self):
        ''' Save the server commands to json file
        '''

        with open('Flandre/data/serverstuff/custom_commands.json', 'w') as file:
                    json.dump(self.custom_commands, file)
        self.bot.log('info', 'custom_commands.json has been saved due to change.')

    def checkServerCommands(self, server):
        ''' Check if the server has both welcome and leaving as None if so ther server is removed from the list
        '''

        if len(self.custom_commands[server.id]) == 0:
            del self.custom_commands[server.id]
            self.bot.log('info', '{0.name} ({0.id}) has removed server commands'.format(server))

    def addServerCommands(self, server):
        ''' Add the server to custom_commands
        '''

        self.custom_commands[server.id] = {}
        self.bot.log('info', '{0.name} ({0.id}) has added custom commands'.format(server))

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def setwelcomechannel(self, ctx):
        ''' Set the channel command is entered in as the channel for welcome and leaving messages
        '''

        message = ctx.message
        removed = False
        
        # Check if server even has server messages
        if message.server.id in self.messages:
            # Check if channel is not being removed
            if message.channel.id == self.messages[message.server.id]['channel']:
                self.messages[message.server.id]['channel'] = None
                removed = True
            else:
                self.messages[message.server.id]['channel'] = message.channel.id

            if removed:
                await self.bot.say('This channel will no longer be used as the server messages channel. Default channel will be used instead')
            else:
                await self.bot.say('This channel will now be used as the server message channel')

            self.saveServerMessages()
        else:
            # Add server to self.messages
            self.addServerMessages(message.server)
            self.messages[message.server.id]['channel'] = message.channel.id
            await self.bot.say('This channel will now be used as the server message channel')
            self.saveServerMessages()

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def welcomemessage(self, ctx, *, msg : str = ''):
        ''' Set a custom welcome message. Leave blank to disable message
            %user% - places the user as a mention
            %server% places the server name
        '''

        message = ctx.message

        # Check if server even has server messages
        if message.server.id not in self.messages:
            # Add server to self.messages
            self.addServerMessages(message.server)

        if msg == '':
            self.messages[message.server.id]['welcome'] = None
            await self.bot.say('{0}, Welcome message has been disabled'.format(message.author.mention))
            self.checkServerMessages(message.server)
            self.saveServerMessages()
        else:
            self.messages[message.server.id]['welcome'] = msg
            await self.bot.say('{0}, Welcome message has been set to\n`{1}`'.format(message.author.mention, msg))
            self.saveServerMessages()

    @commands.command(no_pm=True, pass_context=True)
    @permissions.checkAdmin()
    async def leavemessage(self, ctx, *, msg : str = ''):
        ''' Set a custom leave message. Leave blank to disable message
            %user% - places the user as a mention
            %server% places the server name
        '''

        message = ctx.message

        # Check if server even has server messages
        if message.server.id not in self.messages:
            # Add server to self.messages
            self.addServerMessages(message.server)

        if msg == '':
            self.messages[message.server.id]['leave'] = None
            await self.bot.say('{0}, Leave message has been disabled'.format(message.author.mention))
            self.checkServerMessages(message.server)
            self.saveServerMessages()
        else:
            self.messages[message.server.id]['leave'] = msg
            await self.bot.say('{0}, Leave message has been set to\n`{1}`'.format(message.author.mention, msg))
            self.saveServerMessages()

    @commands.command(no_pm=True, pass_context=True)
    async def viewcustom(self, ctx):
        ''' PMs user the custom commands for the server
        '''

        message = ctx.message
        
        if message.server.id not in self.custom_commands:
            await self.bot.say('{0.mention}, This server has no custom commands'.format(message.author))
        else:
            await self.bot.say('{0.mention}, List sent in PM'.format(message.author))

            msg = 'Commands for {0.server.name}\n```\n'
            for com, resp in self.custom_commands[message.server.id].items():
                if len(msg) < 1500:
                    if '\n' in resp:
                        msg += '%{0} : {1}\n'.format(com, "MULTILINE")
                    elif 'http://' in resp or 'https://' in resp:
                        msg += '%{0} : {1}\n'.format(com, "LINK")
                    else:
                        msg += '%{0} : {1}\n'.format(com, resp)
                else:
                    msg += '```'
                    await self.bot.send_message(message.author, msg.format(message))
                    msg = '```\n'

            msg += '```'
            await self.bot.send_message(message.author, msg.format(message))

    @commands.command(no_pm=True, pass_context=True, aliases=["addcus"])
    @permissions.checkAdmin()
    async def addcustom(self, ctx, command : str, response : str):
        ''' Adds a custom command to the server. Make sure command and response are in ""
            Otherwise the first word will be the command and the second will be the response
        '''

        message = ctx.message

        if message.server.id not in self.custom_commands:
            self.addServerCommands(message.server)

        if command in self.custom_commands:
            msg = 'Edited Command: **{0}**'
        else:
            msg = 'Added Command: **{0}**'

        self.custom_commands[message.server.id][command] = response
        self.saveServerCommands()
        await self.bot.say(msg.format(command))

    @commands.command(no_pm=True, pass_context=True, aliases=["delcus"])
    @permissions.checkAdmin()
    async def deletecustom(self, ctx, command : str):
        ''' Delete a custom from the server
        '''

        message = ctx.message
        if message.server.id not in self.custom_commands:
            await self.bot.say('{0.mention}, This server has no custom commands'.format(message.author))
        else:
            if command in self.custom_commands[message.server.id]:
                self.custom_commands[message.server.id].pop(command, None)
                msg = 'Deleted Command: **{0}**'
                await self.bot.say(msg.format(command))
                self.checkServerCommands(message.server)
                self.saveServerCommands()
            else:
                await self.bot.say('{0.mention}, That is not a command in this server')

    async def checkCustomCommand(self, message):
        if message.content.startswith('%') and not message.channel.is_private:
            command = message.content[1:]
            if command in self.custom_commands[message.server.id]:
                await self.bot.send_message(message.channel, self.custom_commands[message.server.id][command])

    async def sendWelcome(self, member):
        server = member.server

        if server.id in self.messages:
            if self.messages[server.id]['welcome'] is not None:
                message = self.messages[server.id]['welcome']
                # Replace welcome message variables with data
                if '%user%' in message:
                    message = message.replace('%user%', member.mention)
                if '%server%' in message:
                    message = message.replace('%server%', server.name)
                # Wait until user has fully loaded before sending message
                await asyncio.sleep(1)
                if self.messages[server.id]['channel'] is None:
                    await self.bot.send_message(server, message)
                else:
                    channel = discord.utils.get(member.server.channels, id=self.messages[server.id]['channel'])
                    await self.bot.send_message(channel, message)

    async def sendLeave(self, member):
        server = member.server

        if server.id in self.messages:
            if self.messages[server.id]['leave'] is not None:
                message = self.messages[server.id]['leave']
                # Replace welcome message variables with data
                if '%user%' in message:
                    message = message.replace('%user%', member.mention)
                if '%server%' in message:
                    message = message.replace('%server%', server.name)
                # Wait until user has fully loaded before sending message
                await asyncio.sleep(1)
                if self.messages[server.id]['channel'] is None:
                    await self.bot.send_message(server, message)
                else:
                    channel = discord.utils.get(member.server.channels, id=self.messages[server.id]['channel'])
                    await self.bot.send_message(channel, message)

def setup(bot):
    n = serverstuff(bot)
    bot.add_listener(n.checkCustomCommand, "on_message")
    bot.add_listener(n.sendWelcome, "on_member_join")
    bot.add_listener(n.sendLeave, "on_member_remove")
    bot.add_cog(n)