import discord
from discord.ext import commands
from FlandreBot.utils.IO import files
from FlandreBot.utils import permissions
from random import randint
from math import floor
import os
import time
import json
import re
import asyncio
import chess
from PIL import Image

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
        self.chess = files("FlandreBot/data/games/chess.json", "load")
        self.settings = files("FlandreBot/config.json", "load")
    
    #Battleship
    
    @commands.group(name="bs", pass_context=True)
    async def _bs(self, ctx):
        """battleship commands"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @_bs.command(name="invite", pass_context=True, no_pm=True)
    async def bsinvite(self, ctx, user : discord.Member=None):
        """invite a user for battleship"""
        await self.invite_game(ctx, user, self.battleship, "FlandreBot/data/games/battleship.json", 'battleship')
            
    @_bs.command(name="accept", pass_context=True, no_pm=True)
    async def bsaccept(self, ctx):
        """accept battleship invite"""
        await self.accept_game(ctx, self.battleship, "FlandreBot/data/games/battleship.json", 'battleship', False, True)
    
    @_bs.command(name="reject", pass_context=True, no_pm=True)
    async def bsreject(self, ctx):  
        """reject battleship invite"""
        await self.reject_game(ctx, self.battleship, "FlandreBot/data/games/battleship.json")
         
    @_bs.command(name="revoke", pass_context=True, no_pm=True)
    async def bsrevoke(self, ctx):  
        """revoke battleship invite"""
        await self.revoke_game(ctx, self.battleship, "FlandreBot/data/games/battleship.json")
            
    @_bs.command(name="forfeit", aliases=["ff"], pass_context=True, no_pm=True)
    async def bsforfeit(self, ctx):  
        """forfeit battleship game"""
        await self.forfeit_game(ctx, self.battleship, "FlandreBot/data/games/battleship.json")
    
    @_bs.command(name="players", pass_context=True)
    async def bsplayers(self, ctx):  
        """Get list of servers you're playing in"""
        await self.players_game(ctx, self.battleship)
    
    @_bs.command(name="play", pass_context=True)
    async def bsplay(self, ctx, serv : int): 
        """Change opponent"""
        await self.against_game(ctx, serv, self.battleship, "FlandreBot/data/games/battleship.json")
        
    @_bs.command(name="show", pass_context=True)
    async def bsshow(self, ctx, *coords):  
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
        server = ctx.message.server
        if channel.is_private:
            if author.id in self.battleship:
                if self.battleship[author.id]['currentserver'] in self.battleship[author.id]['server']:
                    await self.place_game(ctx, author, server, channel, "FlandreBot/data/games/battleship.json", False, coords, True)
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
        server = ctx.message.server
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
                                await self.bot.send_message(author, 'Both players are done! You start first!\nUse "{}bs target coords" to shoot'.format(self.bot.command_prefix))
                                if not user.bot:
                                    await self.bot.send_message(user, 'Both players are done! The enemy starts first')
                            else:
                                self.battleship[author.id]['server'][currentserver]['turn'] = 9
                                self.battleship[user.id]['server'][currentserver]['turn'] = 10
                                self.battleship[author.id]['server'][currentserver]['play'] = False
                                self.battleship[user.id]['server'][currentserver]['play'] = True
                                files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                await self.bot.send_message(author, 'Both players are done! The enemy starts first')
                                if not user.bot:
                                    await self.bot.send_message(user, 'Both players are done! You start first!\nUse "{}bs target coords" to shoot'.format(self.bot.command_prefix))
                                else:
                                    await self.target_game(ctx, user, server, channel, "FlandreBot/data/games/battleship.json", True, None, currentserver, False)
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
        server = ctx.message.server
        if channel.is_private:
            if author.id in self.battleship:
                currentserver = self.battleship[author.id]['currentserver']
                if self.battleship[author.id]['currentserver'] in self.battleship[author.id]['server']:
                    if self.battleship[author.id]['server'][currentserver]['turn'] > 8:
                        if self.battleship[author.id]['server'][currentserver]['play']:
                            getserver = self.bot.get_server(currentserver)
                            userid = self.battleship[author.id]['server'][currentserver]['against']
                            user = discord.utils.get(getserver.members, id=userid)
                            if not user.bot:
                                await self.target_game(ctx, author, server, channel, "FlandreBot/data/games/battleship.json", False, coords, currentserver, True)
                                await asyncio.sleep(0.5)
                            else:
                                await self.target_game(ctx, author, server, channel, "FlandreBot/data/games/battleship.json", False, coords, currentserver, False)
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
    
    #chess
    
    @commands.group(name="chess", pass_context=True)
    async def _chess(self, ctx):
        """chess commands"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
                
    @_chess.command(name="invite", pass_context=True)
    async def chinvite(self, ctx, user : discord.Member=None):  
        """invite a user for chess"""
        await self.invite_game(ctx, user, self.chess, "FlandreBot/data/games/chess.json", 'chess')

    @_chess.command(name="accept", pass_context=True, no_pm=True)
    async def chaccept(self, ctx):
        """accept chess invite"""
        await self.accept_game(ctx, self.chess, "FlandreBot/data/games/chess.json", 'chess', False, True)

    @_chess.command(name="reject", pass_context=True, no_pm=True)
    async def chreject(self, ctx):
        """reject chess invite"""
        await self.reject_game(ctx, self.chess, "FlandreBot/data/games/chess.json")    
        
    @_chess.command(name="revoke", pass_context=True, no_pm=True)
    async def chrevoke(self, ctx):
        """reject chess invite"""
        await self.revoke_game(ctx, self.chess, "FlandreBot/data/games/chess.json")    
    
    @_chess.command(name="forfeit", aliases=["ff"], pass_context=True, no_pm=True)
    async def chforfeit(self, ctx):
        """forfeit chess game"""
        await self.forfeit_game(ctx, self.chess, "FlandreBot/data/games/chess.json")    
    
    @_chess.command(name="players", pass_context=True)
    async def chplayers(self, ctx):  
        """Get list of servers you're playing in"""
        await self.players_game(ctx, self.chess)
        
    @_chess.command(name="play", pass_context=True)
    async def chplay(self, ctx, serv : int): 
        """Change opponent"""
        await self.against_game(ctx, serv, self.chess, "FlandreBot/data/games/chess.json")  
    
    @_chess.command(name="move", pass_context=True)
    async def chmove(self, ctx, *coords):  
        """Show map of current game"""
        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            if author.id in self.chess:
                if self.chess[author.id]['currentserver'] in self.chess[author.id]['server']:
                    currentserver = self.chess[author.id]['currentserver']
                    if self.chess[author.id]['server'][currentserver]['turn'] == 1:
                        getserver = self.bot.get_server(currentserver)
                        userid = self.chess[author.id]['server'][currentserver]['against']
                        user = discord.utils.get(getserver.members, id=userid)
                        board = chess.Board(self.chess[author.id]['server'][currentserver]['board'])
                        
                        if len(coords) == 2:
                            cord = str(coords[0]).lower() + str(coords[1]).lower()
                            if chess.Move.from_uci(cord) in board.legal_moves:
                                movepiece = chess.Move.from_uci(cord)
                                board.push(movepiece)
                                newboard = board.fen()
                                boardimg = self.getboard(newboard, author.id)
                                self.chess[author.id]['server'][currentserver]['board'] = newboard
                                self.chess[user.id]['server'][currentserver]['board'] = newboard
                                self.chess[author.id]['server'][currentserver]['turn'] = 0
                                self.chess[user.id]['server'][currentserver]['turn'] = 1
                                files("FlandreBot/data/games/chess.json", "save", self.chess)
                                await self.bot.send_file(author, boardimg)
                                await self.bot.send_file(user, boardimg)
                                os.remove(boardimg)
                                await self.bot.send_message(author, '\nPlease wait for the other player')
                                await self.bot.send_message(user, '\nYour opponent moved from ' + str(coords[0]).upper() + ' to ' + str(coords[1]).upper() + ', it is your turn now!')
                                if board.is_stalemate() or board.is_insufficient_material() or board.is_game_over():
                                    await self.bot.send_message(author, 'you win!')
                                    await self.bot.send_message(user, 'you lost!')
                            else:
                                await self.bot.send_message(author, 'That is not a valid move!')
                        else:
                            await self.bot.send_message(author, 'Invalid coordinates!')
                    else:
                        await self.bot.send_message(author, "It's not your turn yet!")
                else:
                    await self.bot.send_message(author, 'You are not in a game!')
            else:
                await self.bot.send_message(author, 'You are not in a game!')
        else:
            await self.bot.send_message(author, 'DM only command!')
            
    @_chess.command(name="show", pass_context=True)
    async def chshow(self, ctx, *coords):  
        """Show board of current game"""
        author = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private:
            if author.id in self.chess:
                if self.chess[author.id]['currentserver'] in self.chess[author.id]['server']:
                    currentserver = self.chess[author.id]['currentserver']
                    board = self.chess[author.id]['server'][currentserver]['board']
                    boardimg = self.getboard(board, author.id)
                    await self.bot.send_file(author, boardimg)
                    os.remove(boardimg)
                else:
                    await self.bot.send_message(author, 'You are not in a game!')
            else:
                await self.bot.send_message(author, 'You are not in a game!')
        else:
            await self.bot.send_message(author, 'DM only command!')
    #utility things
    
    #check for channelname
    def get_channel_name(self, channel):
        channelname = channel.name.lower()
        if 'bot' in channelname:
            return False
        return True
    
    #help message
    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages
            
    #everything to make a game

    #invite to game
    async def invite_game(self, ctx, user, db, file, game):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        channelname = channel.name.lower()
        if self.get_channel_name(channel):
            await self.bot.send_message(channel, 'bot channel only!')
            return
        if user != None:
            if user == author:
                await self.bot.send_message(channel, "{} you cant play against yourself".format(author.mention))
                return
            if user == self.bot.user:
                if author.id not in db:
                    db[author.id] = {'server' : {}}
                    files(file, "save", db)
                if server.id not in db[author.id]['server']:
                    if user.id in db:
                        if server.id in db[user.id]['server']:
                            await self.bot.send_message(channel, "{} invited user is already in a game!".format(author.mention))
                            return
                    else:
                        db[user.id] = {'server' : {}}
                        files(file, "save", db)
                    
                    await self.bot.send_message(channel, "{} Invite accepted! Please check DM.".format(author.mention))
                    db[author.id]['server'][server.id] = {'against' : user.id, 'turn' : 0, 'inv' : 'waiting', 'game' : game}
                    db[user.id]['server'][server.id] = {'against' : author.id, 'turn' : 0, 'inv' : 'invited', 'game' : game}
                    files(file, "save", db)
                    await self.accept_game(ctx, db, file, game, True, False)
                    await self.place_game(ctx, user, server, channel, file, True, None, False)
                else:
                    await self.bot.send_message(channel, "{} you're already in a game".format(author.mention))
                return
            if user.bot:
                await self.bot.send_message(channel, "You can't invite other bots for a game.")
                return
            if author.id not in db:
                db[author.id] = {'server' : {}}
                files(file, "save", db)
            if server.id not in db[author.id]['server']:
                if user.id in db:
                    if server.id in db[user.id]['server']:
                        await self.bot.send_message(channel, "{} invited user is already in a game!".format(author.mention))
                        return
                else:
                    db[user.id] = {'server' : {}}
                    files(file, "save", db)
                    
                db[author.id]['server'][server.id] = {'against' : user.id, 'turn' : 0, 'inv' : 'waiting', 'game' : game}
                db[user.id]['server'][server.id] = {'against' : author.id, 'turn' : 0, 'inv' : 'invited', 'game' : game}
                files(file, "save", db)
                
                if game == 'battleship':
                    await self.bot.send_message(channel, "{} invite send! {} Please accept invite with {}bs accept.".format(author.mention, user.mention, self.bot.command_prefix))
                elif game == 'chess':
                    await self.bot.send_message(channel, "{} invite send! {} Please accept invite with {}chess accept.".format(author.mention, user.mention, self.bot.command_prefix))
            else:
                await self.bot.send_message(channel, "{} you're already in a game".format(author.mention))
        else:
            await self.bot.send_message(channel, "{} please include an user".format(author.mention))
    
    #accept invite of game
    async def accept_game(self, ctx, db, file, game, botuser, human):
        """accept battleship invite"""
        if botuser:
            author = self.bot.user
        else:
            author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        channelname = channel.name.lower()
        if self.get_channel_name(channel):
            await self.bot.send_message(channel, 'bot channel only!')
            return
        if author.id in db:
            if server.id in db[author.id]['server']:
                if db[author.id]['server'][server.id]['inv'] == 'invited':
                    db[author.id]['server'][server.id]['inv'] = 'accepted'
                    db[author.id]['server'][server.id]['turn'] = 1
                    userid = db[author.id]['server'][server.id]['against']
                    db[userid]['server'][server.id]['inv'] = 'accepted'
                    db[userid]['server'][server.id]['turn'] = 1
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.send_message(channel, "{} and {} game started! Please check DM.".format(author.mention, user.mention))
                    db[author.id]['currentserver'] = server.id
                    db[user.id]['currentserver'] = server.id
                    db[author.id]['currentchannel'] = channel.id
                    db[user.id]['currentchannel'] = channel.id
                    files(file, "save", db)
                    if game == 'battleship':
                        message = bsBoard + 'SSSSS SSSS\nSSS SSS SS\nUse {}bs place to place the first ship: SSSSS.\nFor example "{}bs place C1 C5"'.format(self.bot.command_prefix, self.bot.command_prefix)
                        db[author.id]['server'][server.id]['coords'] = []
                        db[user.id]['server'][server.id]['coords'] = []
                        files(file, "save", db)
                    elif game == 'chess':
                        board = chess.Board()
                        boardtext = board.fen()
                        chessBoard = self.getboard(boardtext, author.id)
                        message = 'Use "{}chess move from to" to move a chess piece.\nFor example "{}chess move A2 A3"'.format(self.bot.command_prefix, self.bot.command_prefix)
                        db[author.id]['server'][server.id]['board'] = boardtext
                        db[user.id]['server'][server.id]['board'] = boardtext
                        files(file, "save", db)
                    if human:
                        if game == 'battleship':
                            await self.bot.send_message(author, message)
                            await self.bot.send_message(user, message) 
                        elif game == 'chess':
                            await self.bot.send_file(author, chessBoard)
                            await self.bot.send_file(user, chessBoard)
                            os.remove(boardimg)
                            rand = randint(1,100)
                            if rand < 51:
                                db[author.id]['server'][server.id]['turn'] = 1
                                db[user.id]['server'][server.id]['turn'] = 0
                                await self.bot.send_message(author, message + "\nYou're white and you start first!")
                                await self.bot.send_message(user, message + "\nYou're black, please wait for the other player!") 
                                files(file, "save", db)
                            else:
                                db[author.id]['server'][server.id]['turn'] = 0
                                db[user.id]['server'][server.id]['turn'] = 1
                                await self.bot.send_message(author, message + "\nYou're black, please wait for the other player!") 
                                await self.bot.send_message(user, message + "\nYou're white and you start first!")
                                files(file, "save", db)
                    else:
                        if botuser:
                            await self.bot.send_message(user, message) 
                        else:
                            await self.bot.send_message(author, message)
                else:
                    await self.bot.say("{} you don't have an invite!".format(author.mention))
            else:
                await self.bot.say("{} you don't have an invite!".format(author.mention))
        else:
            await self.bot.say("{} you don't have an invite!".format(author.mention))
            
    #reject invite
    async def reject_game(self, ctx, db, file):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        channelname = channel.name.lower()
        if self.get_channel_name(channel):
            await self.bot.send_message(channel, 'bot channel only!')
            return
        if author.id in db:
            if server.id in db[author.id]['server']:
                if db[author.id]['server'][server.id]['inv'] == 'invited':
                    userid = db[author.id]['server'][server.id]['against']
                    db[author.id]['server'].pop(server.id)
                    db[userid]['server'].pop(server.id)
                    files(file, "save", db)
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.say("{} rejected your invite {}".format(author.mention, user.mention))
                else:
                    await self.bot.say("{} you don't have an invite!".format(author.mention))
            else:
                await self.bot.say("{} you don't have an invite!".format(author.mention))
        else:
            await self.bot.say("{} you don't have an invite!".format(author.mention))
    
    #revoke invite
    async def revoke_game(self, ctx, db, file):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        channelname = channel.name.lower()
        if self.get_channel_name(channel):
            await self.bot.send_message(channel, 'bot channel only!')
            return
        if author.id in db:
            if server.id in db[author.id]['server']:
                if db[author.id]['server'][server.id]['inv'] == 'waiting':
                    userid = db[author.id]['server'][server.id]['against']
                    db[author.id]['server'].pop(server.id)
                    db[userid]['server'].pop(server.id)
                    files(file, "save", db)
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.say("{} your invite has been revoked".format(author.mention))
                else:
                    await self.bot.say("{} you didn't invite anyone!".format(author.mention))
            else:
                await self.bot.say("{} you didn't invite anyone!".format(author.mention))
        else:
            await self.bot.say("{} you didn't invite anyone!".format(author.mention))
            
    #forfeit
    async def forfeit_game(self, ctx, db, file):
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        channelname = channel.name.lower()
        if self.get_channel_name(channel):
            await self.bot.send_message(channel, 'bot channel only!')
            return
        if author.id in db:
            if server.id in db[author.id]['server']:
                if db[author.id]['server'][server.id]['inv'] == 'accepted':
                    userid = db[author.id]['server'][server.id]['against']
                    db[author.id]['server'].pop(server.id)
                    db[userid]['server'].pop(server.id)
                    files(file, "save", db)
                    user = discord.utils.get(ctx.message.server.members, id=userid)
                    await self.bot.say("{} won against {}!".format(user.mention, author.mention))
                else:
                    await self.bot.say("{} you're not in a game!".format(author.mention))
            else:
                await self.bot.say("{} you're not in a game!".format(author.mention))
        else:
            await self.bot.say("{} you're not in a game!".format(author.mention))
    
    #get list of players you're playing against
    async def players_game(self, ctx, db):
        author = ctx.message.author
        message = 'list of servers:\n'
        counter = 1
        next = 0
        
        if author.id in db:
            for server in db[author.id]['server']:
                if next < 40:
                    getserver = self.bot.get_server(server)
                    userid = db[author.id]['server'][server]['against']
                    user = discord.utils.get(getserver.members, id=userid)
                    message = message + '\n{}: {} | {}'.format(counter, user.name, user.id)
                    counter = counter + 1
                    next = next + 1
                else:
                    await self.bot.send_message(author, message)
                    message = ''
                    next = 0
                    await asyncio.sleep(1)
            
            await self.bot.send_message(author, message)
        
        else:
            await self.bot.send_message(author, "you're not in a game")
    
    #change opponent
    async def against_game(self, ctx, serv, db, file):
        counter = 1
        author = ctx.message.author
        
        if author.id in db:
            for server in db[author.id]['server']:
                if counter == serv:
                    db[author.id]['currentserver'] = server
                    files(file, "save", db)
                    await self.bot.send_message(author, 'Changed opponent!')
                    return
            await self.bot.send_message(author, "opponent doesn't exist!")
        else:
            await self.bot.send_message(author, "you're not in a game")
     
    #battleship utilities
     
    #check if coords are valid
    def checkValidCoord(self, coord):
        if len(coord) == 2:
            x = ord(coord[:1].lower()) - 96
            y = int(coord[1:])
            if x > 0 and x < 10:
                if y > 0 and y < 10:
                    return True
        return False
    
    #placing ships on board
    async def place_game(self, ctx, author, server, channel, file, botuser, coords, human):
    
        #variables for AI placing
        placing = 1
        row = 0
        turn = 0
        retry = 100
        retries = 0
        
        placement = True
        
        if botuser:
            placing = 6
        
        while placement:    
            
            for running in range(placing):

                if retries >= retry:
                    self.battleship[author.id]['server'][currentserver]['turn'] = 1
                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                    retries = 0
                else:
                    retries = retries + 1
            
                size = 0
                errorcode = 0
                         
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
                
                    #AI picking random coords for placing
                    if botuser:
                        
                        #random starting coordinate
                        randintx = randint(1, 9)
                        randinty = randint(1, 9)
                        
                        coord1 = str(chr(randintx + 96)) + str(randinty)
                        
                        #vertical (0) or horizontal (1)
                        randint1 = randint(0, 1)
                        
                        if randint1 == 0:
                            y2 = randinty + (size - 1)
                            coord2 = str(chr(y2 + 96)) + str(y2)
                        else:
                            x2 = randintx + (size - 1)
                            coord2 = str(chr(x2 + 96)) + str(randinty)
                            
                        coords = [coord1, coord2]
                        
                    
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
                                    if not botuser:
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
                                    if not botuser:
                                        await self.bot.send_message(author, message)
                                    self.battleship[author.id]['server'][currentserver]['turn'] = self.battleship[author.id]['server'][currentserver]['turn'] + 1
                                    files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                                else:
                                    placement = self.errorcode(author, 1, botuser, placement)
                                    if human:
                                        await self.send_error(author, 1)
                            else:
                                placement = self.errorcode(author, 2, botuser, placement)
                                if human:
                                    await self.send_error(author, 2)
                        else:
                            placement = self.errorcode(author, 1, botuser, placement)
                            if human:
                                await self.send_error(author, 1)
                    else:
                        placement = self.errorcode(author, 3, botuser, placement)
                        if human:
                            await self.send_error(author, 3)
                else:
                    placement = self.errorcode(author, 4, botuser, placement)
                    if human:
                        await self.send_error(author, 4)
        
            if botuser and turn == 7:
                placement = False
                self.battleship[author.id]['server'][currentserver]['turn'] = 8
                files("FlandreBot/data/games/battleship.json", "save", self.battleship)
            elif not botuser:
                placement = False

    #target ships on board
    async def target_game(self, ctx, author, server, channel, file, botuser, coords, currentserver, human):
    
        getcoords = True
    
        #AI picking random coords for target
        
        if botuser:
        
            while getcoords:
        
                #random starting coordinate
                randintx = randint(1, 9)
                randinty = randint(1, 9)
                
                coords = str(chr(randintx + 96)) + str(randinty)
                if coords not in self.battleship[author.id]['server'][currentserver]['targets']:
                    getcoords = False
    
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
                            if human:
                                await self.bot.send_message(author, 'You win!')
                                await self.bot.send_message(user, 'You lost!')
                            else:
                                if botuser:
                                    await self.bot.send_message(user, 'You lost!')
                                else:
                                    await self.bot.send_message(author, 'You win!')
                            currentchannel = self.battleship[author.id]['currentchannel']
                            getchannel = self.bot.get_channel(currentchannel)
                            await self.bot.send_message(getchannel, '{} Won against {} in battleship in '.format(author.mention, user.mention) + str(self.battleship[author.id]['server'][currentserver]['turn']) + ' turns!')
                            self.battleship[author.id]['server'].pop(currentserver)
                            self.battleship[userid]['server'].pop(currentserver)
                            files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                        else:
                            message = 'Player' + message + 'Enemy' + enemymessage + 'You hit something at '+ coords + ' and you can shoot again!'
                            if human:
                                await self.bot.send_message(author, message)
                                await self.bot.send_message(user, 'You got hit at ' + coords)
                            else:
                                if botuser:
                                    await self.bot.send_message(user, 'You got hit at ' + coords)
                                    await self.target_game(ctx, author, server, channel, "FlandreBot/data/games/battleship.json", True, None, currentserver, False)
                                    return
                                else:
                                    await self.bot.send_message(author, message)
                                
                    else:
                        replacepos = ytarget * 22 + xtarget * 2 + 6
                        enemymessage = enemymessage[:replacepos-1] + "X" + enemymessage[replacepos:]
                        self.battleship[author.id]['server'][currentserver]['targets'].append(coords)
                        self.battleship[author.id]['server'][currentserver]['turn'] = self.battleship[author.id]['server'][currentserver]['turn'] + 1
                        files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                        message = 'Player' + message + 'Enemy' + enemymessage + "You missed at "+ coords + ", please wait for the other player's turn"
                        if human:
                            await self.bot.send_message(author, message)
                            await self.bot.send_message(user, "The enemy missed at "+ coords + ", it's your turn now")
                        else:
                            if botuser:
                                await self.bot.send_message(user, "The enemy missed at "+ coords + ", it's your turn now")
                            else:
                                await self.bot.send_message(author, message)
                                await self.target_game(ctx, user, server, channel, "FlandreBot/data/games/battleship.json", True, None, currentserver, False)
                                return
                        self.battleship[author.id]['server'][currentserver]['play'] = False
                        self.battleship[user.id]['server'][currentserver]['play'] = True
                        files("FlandreBot/data/games/battleship.json", "save", self.battleship)
                elif not botuser:
                    await self.send_error(author, 2)
            elif not botuser:
                await self.send_error(author, 1)
        elif not botuser:
            await self.send_error(author, 1)

    def errorcode(self, author, errorcode, botuser, placement):
        if botuser and errorcode != 0:
            return True
        elif botuser and errorcode == 0:
            return placement
        else:
            return False
    
    async def send_error(self, author, errorcode):
        if errorcode == 1:
            await self.bot.send_message(author, 'Invalid coordinates!')
        elif errorcode == 2:
            await self.bot.send_message(author, 'Invalid coordinates! Coordinate has already been used!')
        elif errorcode == 3:
            await self.bot.send_message(author, 'Invalid amount of coordinates!')
        elif errorcode == 4:
            await self.bot.send_message(author, 'You are already done with placing! Please use "{}bs done" or "{}bs reset"'.format(self.bot.command_prefix, self.bot.command_prefix))
    
    #Chess utility

    #show board text
    def getboard(self, board, name):
        boardimg = Image.open("FlandreBot/images/board.png")
        image = None
        index = 0
        counter = 0
        for i in range(0, 64):
            if board[index] == '/' and counter == 0:
                index = index + 1
            if counter == 0:
                if board[index] == 'r':
                    image = Image.open("FlandreBot/images/RB.png")
                elif board[index] == 'n':
                    image = Image.open("FlandreBot/images/KB.png")
                elif board[index] == 'b':
                    image = Image.open("FlandreBot/images/BB.png")
                elif board[index] == 'q':
                    image = Image.open("FlandreBot/images/QB.png")
                elif board[index] == 'k':
                    image = Image.open("FlandreBot/images/KiB.png")
                elif board[index] == 'p':
                    image = Image.open("FlandreBot/images/PB.png")
                elif board[index] == 'P':
                    image = Image.open("FlandreBot/images/PW.png")
                elif board[index] == 'R':
                    image = Image.open("FlandreBot/images/RW.png")
                elif board[index] == 'N':
                    image = Image.open("FlandreBot/images/KW.png")
                elif board[index] == 'B':
                    image = Image.open("FlandreBot/images/BW.png")
                elif board[index] == 'Q':
                    image = Image.open("FlandreBot/images/QW.png")
                elif board[index] == 'K':
                    image = Image.open("FlandreBot/images/KiW.png")

            try:
                if counter == 0:
                    counter = int(board[index]) - 1
                    if counter < 0:
                        counter = 0
                    index = index + 1
                else:
                    counter = counter - 1
            except:
                pass
            
            if image is not None:
                index = index + 1
                row = floor(i / 8)
                column = (i % 8)
                boardimg.paste(image, (20 + column*50, 20 + row*50), image)
                image = None
        boardimg.save('FlandreBot/images/board' + name + '.png')
        return 'FlandreBot/images/board' + name + '.png'
            
    
def check_folders():
    if not os.path.exists("FlandreBot/data/games"):
        print("Creating FlandreBot/data/games folder...")
        os.makedirs("FlandreBot/data/games")

def check_files():
    if not os.path.isfile("FlandreBot/data/games/battleship.json"):
        print("Creating empty battleship.json...")
        files("FlandreBot/data/games/battleship.json", "save", {})
    if not os.path.isfile("FlandreBot/data/games/chess.json"):
        print("Creating empty chess.json...")
        files("FlandreBot/data/games/chess.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = games(bot)
    bot.add_cog(n)