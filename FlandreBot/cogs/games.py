import discord
from discord.ext import commands
from FlandreBot.utils.IO import files
from FlandreBot.utils import permissions
from random import randint
import os
import time
import json
import re

bsBoard = """
```
  A B C D E F G H I  
1| | | | | | | | | | 
2| | | | | | | | | | 
3| | | | | | | | | | 
4| | | | | | | | | | 
5| | | | | | | | | | 
6| | | | | | | | | | 
7| | | | | | | | | | 
8| | | | | | | | | | 
9| | | | | | | | | | 
```
"""

class games:
    
    def __init__(self, bot):
        self.bot = bot
        self.battleship = files("FlandreBot/data/games/battleship.json", "load")
        self.settings = files("FlandreBot/config.json", "load")
        
    @commands.group(name="bs", pass_context=True)
    async def _bs(self, ctx):
        """battleship commands"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @_bs.command(pass_context=True, no_pm=True)
    async def invite(self, ctx, user : discord.Member=None):
        """invite an user for battleship"""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        if user != None:
            if user == author:
                await self.bot.say("{} you cant play against yourself".format(author.mention))
                return
            if author.id not in self.battleship:
                self.battleship[author.id] = {'server' : {}}
                files("FlandreBot/data/games/battleship.json", "save", self.battleship)
            if server.id not in self.battleship[author.id]['server']:
                if user.id in self.battleship:
                    if server.id in self.battleship[user.id]['server']:
                        await self.bot.send_message(channel, "{} invited user is already in a game!".format(author.mention))
                        return
                else:
                    self.battleship[user.id] = {'server' : {}}
                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                    
                self.battleship[author.id]['server'][server.id] = {'against' : user.id, 'turn' : 0, 'inv' : 'waiting', 'game' : 'battleship'}
                self.battleship[user.id]['server'][server.id] = {'against' : author.id, 'turn' : 0, 'inv' : 'invited', 'game' : 'battleship'}
                files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                await self.bot.send_message(channel, "{} invite send!".format(author.mention))
            else:
                await self.bot.send_message(channel, "{} you're already in a game".format(author.mention))
        else:
            await self.bot.say("{} please include an user".format(author.mention))
            
    @_bs.command(pass_context=True, no_pm=True)
    async def accept(self, ctx):
        """accept battleship invite"""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        if author.id in self.battleship:
            if server.id in self.battleship[author.id]['server']:
                if self.battleship[author.id]['server'][server.id]['inv'] == 'invited':
                    self.battleship[author.id]['server'][server.id]['inv'] = 'accepted'
                    self.battleship[author.id]['server'][server.id]['turn'] = 1
                    userid = self.battleship[author.id]['server'][server.id]['against']
                    self.battleship[userid]['server'][server.id]['inv'] = 'accepted'
                    self.battleship[userid]['server'][server.id]['turn'] = 1
                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.say("{} and {} game started! Please check DM".format(author.mention, user.mention))
                    self.battleship[author.id]['server'][server.id]['coords'] = []
                    self.battleship[user.id]['server'][server.id]['coords'] = []
                    self.battleship[author.id]['currentserver'] = server.id
                    self.battleship[user.id]['currentserver'] = server.id
                    self.battleship[author.id]['currentchannel'] = channel.id
                    self.battleship[user.id]['currentchannel'] = channel.id
                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                    message = bsBoard + 'SSSSS SSSS\nSSS SSS SS\nUse {}bs place to place the first ship: SSSSS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                    await self.bot.send_message(author, message)
                    await self.bot.send_message(user, message)
                    
                else:
                    await self.bot.say("{} you don't have an invite!".format(author.mention))
            else:
                await self.bot.say("{} you don't have an invite!".format(author.mention))
        else:
            await self.bot.say("{} you don't have an invite!".format(author.mention))
            
    @_bs.command(pass_context=True, no_pm=True)
    async def reject(self, ctx):  
        """reject battleship invite"""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        if author.id in self.battleship:
            if server.id in self.battleship[author.id]['server']:
                if self.battleship[author.id]['server'][server.id]['inv'] == 'invited':
                    userid = self.battleship[author.id]['server'][server.id]['against']
                    self.battleship[author.id]['server'].pop(server.id)
                    self.battleship[userid]['server'].pop(server.id)
                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.say("{} rejected your invite {}".format(author.mention, user.mention))
                else:
                    await self.bot.say("{} you don't have an invite!".format(author.mention))
            else:
                await self.bot.say("{} you don't have an invite!".format(author.mention))
        else:
            await self.bot.say("{} you don't have an invite!".format(author.mention))
         
    @_bs.command(pass_context=True, no_pm=True)
    async def revoke(self, ctx):  
        """revoke battleship invite"""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        if author.id in self.battleship:
            if server.id in self.battleship[author.id]['server']:
                if self.battleship[author.id]['server'][server.id]['inv'] == 'waiting':
                    userid = self.battleship[author.id]['server'][server.id]['against']
                    self.battleship[author.id]['server'].pop(server.id)
                    self.battleship[userid]['server'].pop(server.id)
                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.say("{} your invite has been revoked".format(author.mention))
                else:
                    await self.bot.say("{} you didn't invite anyone!".format(author.mention))
            else:
                await self.bot.say("{} you didn't invite anyone!".format(author.mention))
        else:
            await self.bot.say("{} you didn't invite anyone!".format(author.mention))
            
    @_bs.command(aliases=["ff"], pass_context=True, no_pm=True)
    async def forfeit(self, ctx):  
        """forfeit battleship game"""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        if author.id in self.battleship:
            if server.id in self.battleship[author.id]['server']:
                if self.battleship[author.id]['server'][server.id]['inv'] == 'accepted':
                    userid = self.battleship[author.id]['server'][server.id]['against']
                    self.battleship[author.id]['server'].pop(server.id)
                    self.battleship[userid]['server'].pop(server.id)
                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.say("{} won against {}!".format(user.mention, author.mention))
                else:
                    await self.bot.say("{} you're not in a game!".format(author.mention))
            else:
                await self.bot.say("{} you're not in a game!".format(author.mention))
        else:
            await self.bot.say("{} you're not in a game!".format(author.mention))
    
    @_bs.command(pass_context=True)
    async def show(self, ctx, *coords):  
        """Show map of current game"""
        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            if author.id in self.battleship:
                if self.battleship[author.id]['currentserver'] in self.battleship[author.id]['server']:
                    currentserver = self.battleship[author.id]['currentserver']
                    turn = self.battleship[author.id]['server'][currentserver]['turn']
                    message = bsBoard
                    enemymessage = bsBoard
                    if turn > 1:
                        #player's board only
                        for coorddraw in self.battleship[author.id]['server'][currentserver]['coords']:
                            x = ord(coorddraw[:1].lower()) - 96
                            y = int(coorddraw[1:])
                            replacepos = y * 22 + x * 2 + 6
                            message = message[:replacepos-1] + "S" + message[replacepos:]
                    
                    if turn > 8:
                        #draw player's board and enemy's board
                        
                        getserver = self.bot.get_server(currentserver)
                        userid = self.battleship[author.id]['server'][currentserver]['against']
                        user = discord.utils.get(getserver.members, id=userid)
                        
                        for coorddraw in self.battleship[author.id]['server'][currentserver]['coords']:
                            x = ord(coorddraw[:1].lower()) - 96
                            y = int(coorddraw[1:])
                            replacepos = y * 22 + x * 2 + 6
                            message = message[:replacepos-1] + "S" + message[replacepos:]
                        
                        for targetdraw in self.battleship[user.id]['server'][currentserver]['targets']:
                            x = ord(targetdraw[:1].lower()) - 96
                            y = int(targetdraw[1:])
                            replacepos = y * 22 + x * 2 + 6
                            if message[replacepos] == 'S':
                                message = message[:replacepos-1] + "O" + message[replacepos:]
                            else:
                                message = message[:replacepos-1] + "X" + message[replacepos:]
                        
                        #draw enemy's board
                        
                        for targetdraw in self.battleship[author.id]['server'][currentserver]['targets']:
                            x = ord(targetdraw[:1].lower()) - 96
                            y = int(targetdraw[1:])
                            replacepos = y * 22 + x * 2 + 6
                            if targetdraw in self.battleship[user.id]['server'][currentserver]['coords']:
                                enemymessage = enemymessage[:replacepos-1] + "O" + enemymessage[replacepos:]
                            else:
                                enemymessage = enemymessage[:replacepos-1] + "X" + enemymessage[replacepos:]
                    
                    message = 'Player' + message + 'Enemy' + enemymessage
                    await self.bot.send_message(author, message)
                else:
                    await self.bot.send_message(author, 'You are not in a game!')
            else:
                await self.bot.send_message(author, 'You are not in a game!')
        else:
            await self.bot.send_message(author, 'DM only command!')
        
    @_bs.command(pass_context=True)
    async def place(self, ctx, *coords):  
        """Place ship in battleship (DM only!)"""
        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            if author.id in self.battleship:
                if self.battleship[author.id]['currentserver'] in self.battleship[author.id]['server']:
                    size = 0
                    
                    #check for size of ship during placement
                    currentserver = self.battleship[author.id]['currentserver']
                    turn = self.battleship[author.id]['server'][currentserver]['turn']
                    shipmessage = ''
                    if turn == 1:
                        size = 5
                        shipmessage = 'SSSS\nSSS SSS SS SS\nUse {}bs place to place the first ship: SSSS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                    elif turn == 2:
                        size = 4
                        shipmessage = 'SSS SSS SS SS\nUse {}bs place to place the first ship: SSS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                    elif turn == 3:
                        size = 3
                        shipmessage = 'SSS SS SS\nUse {}bs place to place the first ship: SSS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                    elif turn == 4:
                        size = 3
                        shipmessage = 'SS SS\nUse {}bs place to place the first ship: SS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                    elif turn == 5:
                        size = 2
                        shipmessage = 'SS\nUse {}bs place to place the first ship: SS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                    elif turn == 6:
                        size = 2
                        shipmessage = 'use "{}bs done" if you are done or "{}bs reset" to start over with placing'.format(self.bot.command_prefix, self.bot.command_prefix)
                    
                    if size != 0:
                        
                        #check if 2 coords is given
                        
                        if len(coords) == 2:
                            coord1 = coords[0]
                            coord2 = coords[1]
                            
                            #check if the coords is valid

                            if self.checkValidCoord(coord1) and self.checkValidCoord(coord2):
                                x1 = ord(coord1[:1].lower()) - 96
                                y1 = int(coord1[1:])
                                x2 = ord(coord2[:1].lower()) - 96
                                y2 = int(coord2[1:])
                                
                                #check if coords is already used

                                valid = True
                                if (y2 - y1) == 0:
                                    for i in range(0, size):
                                        checkCoord = str(chr(x1+96 + i)) + str(y1)
                                        if checkCoord in self.battleship[author.id]['server'][currentserver]['coords']:
                                            valid = False
                                elif (x2 - x1) == 0:
                                    for i in range(0, size):
                                        checkCoord = str(chr(x1+96)) + str(y1 + i)
                                        if checkCoord in self.battleship[author.id]['server'][currentserver]['coords']:
                                            valid = False
                                    

                                #draw map
                                
                                message = bsBoard
                                for coorddraw in self.battleship[author.id]['server'][currentserver]['coords']:
                                    x = ord(coorddraw[:1].lower()) - 96
                                    y = int(coorddraw[1:])
                                    replacepos = y * 22 + x * 2 + 6
                                    message = message[:replacepos-1] + "S" + message[replacepos:]
                                        
                                #check if the distance is valid
                                
                                if valid:
                                    if (y2 - y1) == 0 and (x2 - x1) == (size-1):
                                        for i in range(0, size):
                                            replacepos = y1 * 22 + x1 * 2 + 6 + (i*2)
                                            message = message[:replacepos-1] + "S" + message[replacepos:]
                                            self.battleship[author.id]['server'][currentserver]['coords'].append(str(chr(x1+96 + i)) + str(y1))
                                            files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                        message = message + shipmessage
                                        await self.bot.send_message(author, message)
                                        self.battleship[author.id]['server'][currentserver]['turn'] = self.battleship[author.id]['server'][currentserver]['turn'] + 1
                                        files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                    elif (y2 - y1) == (size-1) and (x2 - x1) == 0:
                                        for i in range(0, size):
                                            replacepos = y1 * 22 + i*22 + x1 * 2 + 6
                                            message = message[:replacepos-1] + "S" + message[replacepos:]
                                            self.battleship[author.id]['server'][currentserver]['coords'].append(str(chr(x1+96)) + str(y1 + i))
                                            files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                        message = message + shipmessage
                                        await self.bot.send_message(author, message)
                                        self.battleship[author.id]['server'][currentserver]['turn'] = self.battleship[author.id]['server'][currentserver]['turn'] + 1
                                        files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                    else:
                                        await self.bot.send_message(author, 'Invalid coordinates!')
                                else:
                                    await self.bot.send_message(author, 'Invalid coordinates! Coordinate has already been used!')
                            else:
                                await self.bot.send_message(author, 'Invalid coordinates!')
                        else:
                            await self.bot.send_message(author, 'Invalid amount of coordinates!')
                    else:
                        await self.bot.send_message(author, 'You are already done with placing! Please use "{}bs done" or "{}bs reset"'.format(self.bot.command_prefix, self.bot.command_prefix))
                else:
                    await self.bot.send_message(author, 'You are not in a game!')
            else:
                await self.bot.send_message(author, 'You are not in a game!')
        else:
            await self.bot.send_message(author, 'DM only command!')
    
    @_bs.command(pass_context=True)
    async def done(self, ctx, *coords):  
        """When you're done with placing (DM only!)"""
        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            if author.id in self.battleship:
                if self.battleship[author.id]['currentserver'] in self.battleship[author.id]['server']:
                    currentserver = self.battleship[author.id]['currentserver']
                    turn = self.battleship[author.id]['server'][currentserver]['turn']
                    if turn == 7:
                        self.battleship[author.id]['server'][currentserver]['turn'] = 8
                        files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                        await self.bot.send_message(author, 'Done! Please wait for the other player.')
                        
                        #if both players are done
                        getserver = self.bot.get_server(currentserver)
                        userid = self.battleship[author.id]['server'][currentserver]['against']
                        user = discord.utils.get(getserver.members, id=userid)
                        
                        if self.battleship[user.id]['server'][currentserver]['turn'] == 8:
                            self.battleship[author.id]['server'][currentserver]['targets'] = []
                            self.battleship[user.id]['server'][currentserver]['targets'] = []
                            self.battleship[author.id]['server'][currentserver]['hits'] = 0
                            self.battleship[user.id]['server'][currentserver]['hits'] = 0
                            
                            rand = randint(1,100)
                            if rand < 51:
                                self.battleship[author.id]['server'][currentserver]['turn'] = 10
                                self.battleship[user.id]['server'][currentserver]['turn'] = 9
                                self.battleship[author.id]['server'][currentserver]['play'] = True
                                self.battleship[user.id]['server'][currentserver]['play'] = False
                                files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                await self.bot.send_message(author, 'Both players are done! You start first!\nUse "{}target coords" to shoot'.format(self.bot.command_prefix))
                                await self.bot.send_message(user, 'Both players are done! The enemy starts first')
                            else:
                                self.battleship[author.id]['server'][currentserver]['turn'] = 9
                                self.battleship[user.id]['server'][currentserver]['turn'] = 10
                                self.battleship[author.id]['server'][currentserver]['play'] = False
                                self.battleship[user.id]['server'][currentserver]['play'] = True
                                files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                await self.bot.send_message(author, 'Both players are done! The enemy starts first')
                                await self.bot.send_message(user, 'Both players are done! You start first!\nUse "{}target coords" to shoot'.format(self.bot.command_prefix))
                    else:
                        await self.bot.send_message(author, 'You are not done yet or already playing!')
                else:
                    await self.bot.send_message(author, 'You are not in a game!')
            else:
                await self.bot.send_message(author, 'You are not in a game!')
        else:
            await self.bot.send_message(author, 'DM only command!')
            
    @_bs.command(pass_context=True)
    async def reset(self, ctx, *coords):  
        """Resets the placing (DM only!)"""
        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            if author.id in self.battleship:
                if self.battleship[author.id]['currentserver'] in self.battleship[author.id]['server']:
                    currentserver = self.battleship[author.id]['currentserver']
                    turn = self.battleship[author.id]['server'][currentserver]['turn']
                    if turn > 0 or turn < 8:
                        self.battleship[author.id]['server'][currentserver]['turn']= 1
                        self.battleship[author.id]['server'][currentserver]['coords'] = []
                        files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                        message = bsBoard + 'SSSSS SSSS\n SSS SSS SS\nUse {}bs place to place the first ship: SSSSS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                        await self.bot.send_message(author, message)
                    else:
                        await self.bot.send_message(author, 'You cannot reset now!')
                else:
                    await self.bot.send_message(author, 'You are not in a game!')
            else:
                await self.bot.send_message(author, 'You are not in a game!')
        else:
            await self.bot.send_message(author, 'DM only command!')
    
    @_bs.command(pass_context=True)
    async def target(self, ctx, coords):  
        """Shoot at enemy's battleship (DM only!)"""
        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            if author.id in self.battleship:
                currentserver = self.battleship[author.id]['currentserver']
                if self.battleship[author.id]['currentserver'] in self.battleship[author.id]['server']:
                    if self.battleship[author.id]['server'][currentserver]['turn'] > 8:
                        if self.battleship[author.id]['server'][currentserver]['play']:
                            
                            #check if the coords is valid
                            if len(coords) == 2:
                                if self.checkValidCoord(coords):
                                    x = ord(coords[:1].lower()) - 96
                                    y = int(coords[1:])

                                    #check if coords has been used before
                                    valid = True
                                    if coords.lower() in self.battleship[author.id]['server'][currentserver]['targets']:
                                        valid = False
                                        
                                    #draw map
                                    
                                    message = bsBoard
                                    enemymessage = bsBoard
                                    
                                    getserver = self.bot.get_server(currentserver)
                                    userid = self.battleship[author.id]['server'][currentserver]['against']
                                    user = discord.utils.get(getserver.members, id=userid)
                                    
                                    xtarget = x
                                    ytarget = y
                                    
                                    #draw player's board
                                    for coorddraw in self.battleship[author.id]['server'][currentserver]['coords']:
                                        x = ord(coorddraw[:1].lower()) - 96
                                        y = int(coorddraw[1:])
                                        replacepos = y * 22 + x * 2 + 6
                                        message = message[:replacepos-1] + "S" + message[replacepos:]
                                    
                                    for targetdraw in self.battleship[user.id]['server'][currentserver]['targets']:
                                        x = ord(targetdraw[:1].lower()) - 96
                                        y = int(targetdraw[1:])
                                        replacepos = y * 22 + x * 2 + 6
                                        if message[replacepos] == 'S':
                                            message = message[:replacepos-1] + "O" + message[replacepos:]
                                        else:
                                            message = message[:replacepos-1] + "X" + message[replacepos:]
                                    
                                    #draw enemy's board
                                    
                                    for targetdraw in self.battleship[author.id]['server'][currentserver]['targets']:
                                        x = ord(targetdraw[:1].lower()) - 96
                                        y = int(targetdraw[1:])
                                        replacepos = y * 22 + x * 2 + 6
                                        if targetdraw in self.battleship[user.id]['server'][currentserver]['coords']:
                                            enemymessage = enemymessage[:replacepos-1] + "O" + enemymessage[replacepos:]
                                        else:
                                            enemymessage = enemymessage[:replacepos-1] + "X" + enemymessage[replacepos:]
                                    
                                    #if its valid: shoot the target
                                    
                                    if valid:
                                        replacepos = ytarget * 22 + xtarget * 2 + 6
                                        if coords in self.battleship[user.id]['server'][currentserver]['coords']:
                                            enemymessage = enemymessage[:replacepos-1] + "O" + enemymessage[replacepos:]
                                            self.battleship[author.id]['server'][currentserver]['targets'].append(coords)
                                            self.battleship[author.id]['server'][currentserver]['hits'] = self.battleship[author.id]['server'][currentserver]['hits'] + 1
                                            self.battleship[author.id]['server'][currentserver]['turn'] = self.battleship[author.id]['server'][currentserver]['turn'] + 1
                                            files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                            if len(self.battleship[author.id]['server'][currentserver]['coords']) == self.battleship[author.id]['server'][currentserver]['hits']:
                                                await self.bot.send_message(author, 'You win!')
                                                await self.bot.send_message(user, 'You lost!')
                                                currentchannel = self.battleship[author.id]['currentchannel']
                                                getchannel = self.bot.get_channel(currentchannel)
                                                await self.bot.send_message(getchannel, '{} Won against {} in battleship in '.format(author.mention, user.mention) + str(self.battleship[author.id]['server'][currentserver]['turn']) + ' turns!')
                                                self.battleship[author.id]['server'].pop(currentserver)
                                                self.battleship[userid]['server'].pop(currentserver)
                                                files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                            else:
                                                message = 'Player' + message + 'Enemy' + enemymessage + 'You hit something and you can shoot again!'
                                                await self.bot.send_message(author, message)
                                                await self.bot.send_message(user, 'You got hit at ' + coords)
                                        else:
                                            replacepos = ytarget * 22 + xtarget * 2 + 6
                                            enemymessage = enemymessage[:replacepos-1] + "X" + enemymessage[replacepos:]
                                            self.battleship[author.id]['server'][currentserver]['targets'].append(coords)
                                            self.battleship[author.id]['server'][currentserver]['turn'] = self.battleship[author.id]['server'][currentserver]['turn'] + 1
                                            files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                            message = 'Player' + message + 'Enemy' + enemymessage + "You missed, please wait for the other player's turn"
                                            await self.bot.send_message(author, message)
                                            await self.bot.send_message(user, "The enemy missed, it's your turn now")
                                            self.battleship[author.id]['server'][currentserver]['play'] = False
                                            self.battleship[user.id]['server'][currentserver]['play'] = True
                                            files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                    else:
                                        await self.bot.send_message(author, 'Invalid coordinates! Coordinate has already been used!')
                                else:
                                    await self.bot.send_message(author, 'Invalid coordinates!')
                            else:
                                await self.bot.send_message(author, 'Invalid coordinates!')
                        else:
                            await self.bot.send_message(author, 'It is not your turn yet.')
                    else:
                        await self.bot.send_message(author, 'The game has not been started yet!.')
                else:
                    await self.bot.send_message(author, 'You are not in a game!')
            else:
                await self.bot.send_message(author, 'You are not in a game!')
        else:
            await self.bot.send_message(author, 'DM only command!')
    
    def checkValidCoord(self, coord):
        if len(coord) == 2:
            x = ord(coord[:1].lower()) - 96
            y = int(coord[1:])
            if x > 0 and x < 10:
                if y > 0 and y < 10:
                    return True
        return False
    
    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages
     
            
def check_folders():
    if not os.path.exists("FlandreBot/data/games"):
        print("Creating FlandreBot/data/games folder...")
        os.makedirs("FlandreBot/data/games")

def check_files():
    if not os.path.isfile("FlandreBot/data/games/battleship.json"):
        print("Creating empty battleship.json...")
        files("FlandreBot/data/games/battleship.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = games(bot)
    bot.add_cog(n)