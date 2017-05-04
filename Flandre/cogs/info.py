import discord
from discord.ext import commands
from Flandre import permissions
import os
import time
import json
import re
import asyncio

ownerid = "130012001236811776"
serverid = "152095665114054657"
invitelink = "https://discord.gg/0qflKzPpiEv9y26o"


class info:
    
    def __init__(self, bot):
        self.bot = bot
        self.serverlist = []
        self.channellist = []
        self.users = []
        self.currentserver = ''
        self.currentchannel = ''
        self.currentuser = ''
    
    @commands.command(pass_context=True)
    async def ownerinfo(self, ctx):
        """Get information of the bot"""
        
        author = ctx.message.author
        
        server = self.bot.get_server(serverid)
        user = discord.utils.get(server.members, id=ownerid)
        
        embedcolour = discord.Colour(16776960)
        userembed = discord.Embed(type='rich', colour=embedcolour)
        userembed.add_field(name='Owner of bot', value=user.name + "#" + user.discriminator)
        userembed.add_field(name='Owner ID', value=user.id)
        userembed.set_thumbnail(url=user.avatar_url)
        
        await self.bot.send_message(author, embed=userembed)
        await self.bot.send_message(author, invitelink)

    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def notify(self, ctx, *text):  
        """noitify something in all servers"""
        
        for server in self.bot.servers:
            if text != None:
                channel = server.default_channel
                message = ''
                for t in text:
                    message = message + " " + t
                message = message[1:]

                if 'MENTION' in message and self.currentuser != '':
                    server = self.bot.get_server(self.currentserver)
                    user = discord.utils.get(server.members, id=self.currentuser)
                    message = message.replace("MENTION", user.mention)
                
                await self.bot.send_message(channel, message)
            else:
                await self.bot.say("Please enter a message")
        
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def servers(self, ctx):  
        """Get list of servers the bot is in"""
        
        author = ctx.message.author
        message = ''
        counter = 1
        self.serverlist = []
        next = 0
        
        for server in self.bot.servers:
            if next < 40:
                message = message + '\n{}: {} | {}'.format(counter, server.name, server.id)
                counter = counter + 1
                self.serverlist.append(server.id)
                next = next + 1
            else:
                await self.bot.send_message(author, message)
                message = ''
                next = 0
                await asyncio.sleep(1)
        
        await self.bot.send_message(author, message)
        
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def setserver(self, ctx, server : int):  
        """Set server to do stuff"""

        server = server - 1
        
        if server < len(self.serverlist):
            currentserver = self.serverlist[server]
            getserver = self.bot.get_server(currentserver)
            self.currentserver = currentserver
            await self.bot.say('Changed server to: {}'.format(getserver.name))
        else:
            await self.bot.say('Invalid selection')
    
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def channels(self, ctx):  
        """Get list of channels of server"""
        
        author = ctx.message.author
        message = ""
        counter = 1
        next = 0
        self.channellist = []
        
        if self.currentserver != '':
            server = self.bot.get_server(self.currentserver)
            
            for channel in server.channels:
                if next < 40:
                    if str(channel.type) == 'text':
                        message = message + '\n{}: {} | {}'.format(counter, channel.name, channel.id)
                        counter = counter + 1
                        self.channellist.append(channel.id)
                        next = next + 1
                else:
                    await self.bot.send_message(author, message)
                    message = ''
                    next = 0
                    await asyncio.sleep(1)
                
            await self.bot.send_message(author, message)
        else:
            await self.bot.say("Please set a server")
            
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def setchannel(self, ctx, channelnumb : int):          
        """Set channel of server"""
        
        if self.currentserver != '':
            server = self.bot.get_server(self.currentserver)
                
            channelnumb = channelnumb - 1
            
            if channelnumb < len(self.channellist):
                currentchannel = self.channellist[channelnumb]
                getchannel = self.bot.get_channel(currentchannel)
                self.currentchannel = currentchannel
                await self.bot.say('Changed channel to: {}'.format(getchannel.name))
            else:
                await self.bot.say('Invalid selection')
        else:
            await self.bot.say("Please set a server")
      
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def userlist(self, ctx):    
        """Get list of users of server"""
        
        author = ctx.message.author
        message = ''
        counter = 1
        self.users = []
        next = 0
        
        if self.currentserver != '':
            server = self.bot.get_server(self.currentserver)
            
            for user in server.members:
                if next < 40:
                    message = message + '\n{}: {} | {}'.format(counter, user.name, user.id)
                    counter = counter + 1
                    self.users.append(user.id)
                    next = next + 1
                else:
                    await self.bot.send_message(author, message)
                    message = ''
                    next = 0
                    await asyncio.sleep(1)
                
            await self.bot.send_message(author, message)
        else:
            await self.bot.say("Please set a server")
            
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def getuser(self, ctx, username : str):    
        """Get list of users of server"""
        
        author = ctx.message.author
        message = ''
        counter = 1
        self.users = []
        next = 0
        
        if self.currentserver != '' and username != None:
            server = self.bot.get_server(self.currentserver)
            
            users = server.members

            for user in users:
                if user.name == username:
                    if next < 40:
                        message = message + '\n{}: {} | {}'.format(counter, user.name, user.id)
                        counter = counter + 1
                        self.users.append(user.id)
                        next = next + 1
                    else:
                        await self.bot.send_message(author, message)
                        message = ''
                        next = 0
                        await asyncio.sleep(1)
            if message != '':    
                await self.bot.send_message(author, message)
            else:
                await self.bot.send_message(author, 'No users found')
                    
        else:
            await self.bot.say("Please set a server")
            
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def setuser(self, ctx, usernumb : int):          
        """Set user to mention"""
        
        if self.currentserver != '':
            server = self.bot.get_server(self.currentserver)
                
            usernumb = usernumb - 1
            
            if usernumb < len(self.users):
                currentuser = self.users[usernumb]
                server = self.bot.get_server(self.currentserver)
                user = discord.utils.get(server.members, id=currentuser)
                self.currentuser = user.id
                await self.bot.say('Changed user to: {}'.format(user.name))
            else:
                await self.bot.say('Invalid selection')
        else:
            await self.bot.say("Please set a server")
    
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def say(self, ctx, *text):  
        """Say something with bot in server"""
        
        if self.currentchannel != '':
            if text != None:
                channel = self.bot.get_channel(self.currentchannel)
                message = ''
                for t in text:
                    message = message + " " + t
                message = message[1:]

                if 'MENTION' in message and self.currentuser != '':
                    server = self.bot.get_server(self.currentserver)
                    user = discord.utils.get(server.members, id=self.currentuser)
                    message = message.replace("MENTION", user.mention)
                
                await self.bot.send_message(channel, message)
            else:
                await self.bot.say("Please enter a message")
        else:
            await self.bot.say("Please set a channel")
            
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def getlog(self, ctx, amount : int):  
        """Say something with bot in server"""
        
        
        if self.currentchannel != '':
            channel = self.bot.get_channel(self.currentchannel)
            if amount > 0:
                async for x in self.bot.logs_from(channel, limit=amount):
                    await self.bot.say('{0} {1}: {2}'.format(x.timestamp, x.author.name, x.content))
                    await asyncio.sleep(0.5)
            else:
                await self.bot.say('Please include amount of text')
        else:
            await self.bot.say("Please set a channel")
            
            
    
def setup(bot):
    n = info(bot)
    bot.add_cog(n)