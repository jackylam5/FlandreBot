import discord
from discord.ext import commands
from FlandreBot.utils.IO import files
from FlandreBot.utils import permissions
import os
import time
import json
import re

class serverthings:
    
    def __init__(self, bot):
        self.bot = bot
        self.welcome = files("FlandreBot/data/serverthings/welcome.json", "load")
    
    @commands.group(name="wm", pass_context=True, no_pm=True)
    @permissions.checkAdmin()
    async def wm(self, ctx):
        """Welcome message settings"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @wm.command(pass_context=True, no_pm=True)
    async def wtoggle(self, ctx):
        """Enable or disable welcome message"""
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id in self.welcome:
            self.welcome.pop(server.id)
            await self.bot.say("Welcome message disabled!")
        else:
            self.welcome[server.id] = {'name' : server.name, "welcomeMessage" : """Welcome ?!mention?! to the server ?!server?!!""", 'channel' : channel.id, "leaveMessage" : """?!name?! left the server :(""", "left" : False}
            files("FlandreBot/data/serverthings/welcome.json", "save", self.welcome)
            await self.bot.say("Welcome message enabled!")
            
    @wm.command(pass_context=True, no_pm=True)
    async def forcechannel(self, ctx):      
        """force welcome/leave message channel"""
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id in self.welcome:
            self.welcome[server.id]["channel"] = channel.id
            files("FlandreBot/data/serverthings/welcome.json", "save", self.welcome)
            await self.bot.say("done!")
        else:
            await self.bot.say("Please enable welcome message first")
        
    @wm.command(pass_context=True, no_pm=True)
    async def ltoggle(self, ctx):  
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id in self.welcome:       
            if self.welcome[server.id]["left"]:
                self.welcome[server.id]["left"] = False
                files("FlandreBot/data/serverthings/welcome.json", "save", self.welcome)
                await self.bot.say("Left message disabled")
            else:
                self.welcome[server.id]["left"] = True
                files("FlandreBot/data/serverthings/welcome.json", "save", self.welcome)
                await self.bot.say("Left message enabled")
        else:
            await self.bot.say("Please enable welcome message first")
    
    @wm.command(pass_context=True, no_pm=True)
    async def wmessage(self, ctx, *text : str): 
        server = ctx.message.server
        channel = ctx.message.channel
        if text == None:
            await self.bot.say("Please enter a message")
            return
        message = ""
        for p in text:
            message = message + " " + p
        message = message[1:]
        if server.id in self.welcome:       
            self.welcome[server.id]["welcomeMessage"] = message
            files("FlandreBot/data/serverthings/welcome.json", "save", self.welcome)
            await self.bot.say("changed welcome message!")
        else:
            await self.bot.say("Please enable welcome message first")
        
    @wm.command(pass_context=True, no_pm=True)
    async def lmessage(self, ctx, *text : str): 
        server = ctx.message.server
        channel = ctx.message.channel
        if text == None:
            await self.bot.say("Please enter a message")
            return
        message = ""
        for p in text:
            message = message + " " + p
        message = message[1:]
        if server.id in self.welcome:       
            self.welcome[server.id]["leftMessage"] = message
            files("FlandreBot/data/serverthings/welcome.json", "save", self.welcome)
            await self.bot.say("changed welcome message!")
        else:
            await self.bot.say("Please enable welcome message first")
    
    
    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages
            
    async def member_join(self, member):
        server = member.server
        if server.id in self.welcome: 
            channel = self.bot.get_channel(str(self.welcome[server.id]["channel"]))
            if channel:
                message = self.welcome[server.id]["welcomeMessage"]
                if "?!name?!" in message:
                    message = message.replace("?!name?!", member.name)
                if "?!mention?!" in message:
                    message = message.replace("?!mention?!", member.mention)
                if "?!server?!" in message:
                    message = message.replace("?!server?!", server.name)
                await self.bot.send_message(channel, message)
    
    async def member_left(self, member):
        server = member.server
        if server.id in self.welcome: 
            channel = self.bot.get_channel(str(self.welcome[server.id]["channel"]))
            if channel:
                if self.welcome[server.id]["left"]:
                    message = self.welcome[server.id]["leaveMessage"]
                    if "?!name?!" in message:
                        message = message.replace("?!name?!", member.name)
                    if "?!mention?!" in message:
                        message = message.replace("?!mention?!", member.mention)
                    if "?!server?!" in message:
                        message = message.replace("?!server?!", server.name)
                    await self.bot.send_message(channel, message)
    
def check_folders():
    if not os.path.exists("FlandreBot/data/serverthings"):
        print("Creating FlandreBot/data/serverthings folder...")
        os.makedirs("FlandreBot/data/serverthings")

def check_files():
    if not os.path.isfile("FlandreBot/data/serverthings/welcome.json"):
        print("Creating empty welcome.json...")
        files("FlandreBot/data/serverthings/welcome.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = serverthings(bot)
    bot.add_listener(n.member_join, "on_member_join")
    bot.add_listener(n.member_left, "on_member_remove")
    bot.add_cog(n)