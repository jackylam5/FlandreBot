import discord
from discord.ext import commands
from FlandreBot.utils.IO import files
from FlandreBot.utils import permissions
from discord import Game
from cleverbot import Cleverbot
import os
import time
import json
import re

class serverthings:
    
    def __init__(self, bot):
        self.bot = bot
        self.welcome = files("FlandreBot/data/serverthings/welcome.json", "load")
        self.clever = files("FlandreBot/data/serverthings/clever.json", "load")
        self.settings = files("FlandreBot/config.json", "load")
    
    @commands.group(name="set", pass_context=True)
    @permissions.checkOwner()
    async def _set(self, ctx):
        """Bot settings"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
                
    @_set.command(pass_context=True)
    async def prefix(self, ctx, prefix : str):
        """Change bot's prefix"""
        if prefix != None:
            self.bot.command_prefix = prefix
            self.settings["prefix"] = prefix
            files("FlandreBot/config.json", "save", self.settings)
            await self.bot.say("Changed prefix!")
            
    @_set.command(pass_context=True)
    async def game(self, ctx, playing : str):
        """Change game of bot"""
        if playing != None:
            if playing == "None":
                await self.bot.change_presence(game=None, status=None)
                await self.bot.say("changed game!")
                self.settings["game"] = ""
            else:
                await self.bot.change_presence(game=Game(name=playing), status=None)
                await self.bot.say("changed game!")
                self.settings["game"] = playing

    @_set.command(pass_context=True)
    async def name(self, ctx, name : str):
        """Change nickname of bot"""
        if name != None:
            await self.bot.change_nickname(ctx.message.server.me, name)
            await self.bot.say("Changed my nickname!")
    
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
    
    @commands.group(name="clever", pass_context=True)
    @permissions.checkAdmin()
    async def _clever(self, ctx):
        """Bot settings"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
    
    @_clever.command(pass_context=True, no_pm=True)
    async def allow(self, ctx): 
        """allow server for talking to bot"""
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id not in self.clever:
            self.clever[server.id] = {'channels:' : {}}
            files("FlandreBot/data/serverthings/clever.json", "save", self.clever)
            await self.bot.say("server added to list")
        else:
            self.clever.pop(server.id)
            files("FlandreBot/data/serverthings/clever.json", "save", self.clever)
            await self.bot.say("server removed from list")
            
    @_clever.command(pass_context=True, no_pm=True)
    async def add(self, ctx):         
        """add channel to list"""
        server = ctx.message.server
        channel = ctx.message.channel
        if server.id in self.clever:
            if channel.id not in self.clever[server.id]:
                self.clever[server.id][channel.id] = {'name' : channel.name}
                files("FlandreBot/data/serverthings/clever.json", "save", self.clever)
                await self.bot.say("channel added to list")
            else:
                self.clever[server.id].pop(channel.id)
                files("FlandreBot/data/serverthings/clever.json", "save", self.clever)
                await self.bot.say("channel removed from list")
        else:
            await self.bot.say("server is no on the list yet")
    
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
                    
    async def on_mention_message(self, message):
        if message.server.id in self.clever:
            if message.channel.id in self.clever[message.server.id]:
                if self.bot.user.mentioned_in(message):
                    mess = message.content.split(' ', 1)[1]
                    cleverbot = Cleverbot('FlandreBot')
                    answer = cleverbot.ask(mess)
                    await self.bot.send_message(message.channel, answer)
    
def check_folders():
    if not os.path.exists("FlandreBot/data/serverthings"):
        print("Creating FlandreBot/data/serverthings folder...")
        os.makedirs("FlandreBot/data/serverthings")

def check_files():
    if not os.path.isfile("FlandreBot/data/serverthings/welcome.json"):
        print("Creating empty welcome.json...")
        files("FlandreBot/data/serverthings/welcome.json", "save", {})
    if not os.path.isfile("FlandreBot/data/serverthings/clever.json"):
        print("Creating empty clever.json...")
        files("FlandreBot/data/serverthings/clever.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = serverthings(bot)
    bot.add_listener(n.member_join, "on_member_join")
    bot.add_listener(n.member_left, "on_member_remove")
    bot.add_listener(n.on_mention_message, "on_message")
    bot.add_cog(n)