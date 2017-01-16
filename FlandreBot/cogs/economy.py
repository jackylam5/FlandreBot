import discord
from discord.ext import commands
from FlandreBot.utils.IO import files
from random import randint
from copy import deepcopy
import os
import time
import json
import logging
from FlandreBot.utils import permissions

"""message.channel.name == "gambling"""

slot_payouts = """Slot machine payouts:
    idk too lazy to write this"""

class economy:
    """Economy

    Get rich and have fun with imaginary currency!"""

    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.loadConfig()
        self.bank = files("FlandreBot/data/economy/bank.json", "load")
        self.settings = files("FlandreBot/data/economy/settings.json", "load")
        self.payday_register = {}
        self.slot_register = {}
        
    @commands.group(name="bank", pass_context=True)
    async def _bank(self, ctx):
        """Bank operations"""
        if ctx.message.channel.name == "gambling":
            if ctx.invoked_subcommand is None:
                pages = self.send_cmd_help(ctx)
                for page in pages:
                    await self.bot.send_message(ctx.message.channel, page)
        else:
            await self.bot.say("Gambling room only command")

    @_bank.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an account at the Scrub bank"""
        if ctx.message.channel.name == "gambling":
            user = ctx.message.author
            if user.id not in self.bank:
                self.bank[user.id] = {"name" : user.name, "balance" : 100, "specialcoin" : 0, "coinincrease" : 0, "chanceincrease" : 0, "times": 0, "totalsc" : 0, "startmoney" : 100, "bid" : 0, "currentcard" : 0, "card1" : 0, "card2" : 0, "card3" : 0, "card4" : 0, "card5" : 0, "fase" : 0 }
                files("FlandreBot/data/economy/bank.json", "save", self.bank)
                await self.bot.say("{} Account opened. Current balance: {}".format(user.mention, str(self.check_balance(user.id))))
            else:
                await self.bot.say("{} You already have an account at the Scrub bank.".format(user.mention))
        else:
            pass    
            
            
    @_bank.command(pass_context=True, no_pm=True)
    async def namechange(self, ctx):
        """Change bank name"""
        if ctx.message.channel.name == "gambling":
            user = ctx.message.author
            message = ctx.message
            if user.id in self.bank:
                self.set_name(message.author.id, user.name)
                await self.bot.say("{} Your name in bank has been changed.".format(user.mention))
            else:
                await self.bot.say("{} You don't have an account at the Scrub bank. Type {}bank register to open one.".format(user.mention, ctx.prefix))
        else:
            pass    
            
               
            

    @_bank.command(pass_context=True)
    async def balance(self, ctx, user : discord.Member=None):
        """Shows balance of user.

        Defaults to yours."""
        if ctx.message.channel.name == "gambling":
            if not user:
                user = ctx.message.author
                if self.account_check(user.id):
                    await self.bot.say("{} Your balance is: {}".format(user.mention, str(self.check_balance(user.id))))
                else:
                    await self.bot.say("{} You don't have an account at the Scrub bank. Type {}bank register to open one.".format(user.mention, ctx.prefix))
            else:
                if self.account_check(user.id):
                    balance = self.check_balance(user.id)
                    await self.bot.say("{}'s balance is {}".format(user.name, str(balance)))
                else:
                    await self.bot.say("That user has no bank account.")
        else:
            pass   
            
            
    @_bank.command(pass_context=True)
    async def reset(self, ctx, user : discord.Member=None):
        """Reset balance and get 1 Special coin

        """
        if ctx.message.channel.name == "gambling":
            if not user:
                user = ctx.message.author
                message = ctx.message
                if self.account_check(user.id):
                    if self.check_balance(message.author.id) >= self.settings["MAX_BALANCE"]:
                        startmoney = self.check_startmoney(message.author.id)
                        money = self.check_balance(user.id)
                        self.add_sc(message.author.id, 1)
                        self.add_tsc(message.author.id, 1)
                        self.withdraw_money(message.author.id, money)
                        self.add_money(message.author.id, startmoney)
                        await self.bot.say("{} Your special coins balance is: {}. Total special coins: {}".format(user.mention, str(self.check_specialbalance(user.id)), str(self.check_specialtotalbalance(user.id))))
                    else:
                        await self.bot.say("{} You dont have enough coins.".format(user.mention))
                else:
                    await self.bot.say("{} You don't have an account at the Scrub bank. Type {}bank register to open one.".format(user.mention, ctx.prefix))
            else:
                await self.bot.say("{} You can only reset your own balance.".format(user.mention))
        else:
            pass   
    
    
    
    
    
    @_bank.command(pass_context=True)
    async def transfer(self, ctx, user : discord.Member, sum : int):
        """Transfer coins to other users"""
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            if author == user:
                await self.bot.say("You can't transfer money to yourself.")
                return
            if sum < 1:
                await self.bot.say("You need to transfer at least 1 coin.")
                return
            if self.account_check(user.id):
                if self.enough_money(author.id, sum):
                    self.withdraw_money(author.id, sum)
                    self.add_money(user.id, sum)
                    logger.info("{}({}) transferred {} coins to {}({})".format(author.name, author.id, str(sum), user.name, user.id))
                    await self.bot.say("{} coins have been transferred to {}'s account.".format(str(sum), user.name))
                else:
                    await self.bot.say("You don't have that sum in your bank account.")
            else:
                await self.bot.say("That user has no bank account.")
        else:
            pass 


    @_bank.command(name="set", pass_context=True)
    @permissions.checkOwner()
    async def _set(self, ctx, user : discord.Member, sum : int):
        """Sets money of user's bank account

        Admin/owner restricted."""
        
        author = ctx.message.author
        channel = ctx.message.channel
        
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            done = self.set_money(user.id, sum)
            if done:
                logger.info("{}({}) set {} coins to {} ({})".format(author.name, author.id, str(sum), user.name, user.id))
                await self.bot.say("{}'s coins have been set to {}".format(user.name, str(sum)))
            else:
                await self.bot.say("User has no bank account.")
        else:
            pass 


    @commands.command(pass_context=True, no_pm=True)
    async def payday(self, ctx):
        """Get some free credits"""
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            id = author.id
            if self.account_check(id):
                if id in self.payday_register:
                    seconds = abs(self.payday_register[id] - int(time.perf_counter()))
                    if seconds  >= self.settings["PAYDAY_TIME"]:
                        self.add_money(id, self.settings["PAYDAY_CREDITS"])
                        self.payday_register[id] = int(time.perf_counter())
                        await self.bot.say("{} Here, take some coins. Enjoy! (+{} coins!)".format(author.mention, str(self.settings["PAYDAY_CREDITS"])))
                    else:
                        await self.bot.say("{} Too soon. For your next payday you have to wait {}.".format(author.mention, self.display_time(self.settings["PAYDAY_TIME"] - seconds)))
                else:
                    self.payday_register[id] = int(time.perf_counter())
                    self.add_money(id, self.settings["PAYDAY_CREDITS"])
                    await self.bot.say("{} Here, take some coins. Enjoy! (+{} coins!)".format(author.mention, str(self.settings["PAYDAY_CREDITS"])))
            else:
                await self.bot.say("{} You need an account to receive coins.".format(author.mention))
        else:
            await self.bot.say("Gambling room only command")
            
            
    @commands.command()
    async def leaderboard(self, top : int=10):
        """Prints out the leaderboard of coins

        Defaults to top 10""" #Originally coded by Airenkun - edited by irdumb
        if top < 1:
            top = 10
        bank_sorted = sorted(self.bank.items(), key=lambda x: x[1]["balance"], reverse=True)
            
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        topten = bank_sorted[:top]
        highscore = ""
        place = 1

        for id in topten:
            highscore += str(place).ljust(len(str(top))+1)
            highscore += (id[1]["name"]+" ").ljust(23-len(str(id[1]["balance"])))
            highscore += str(id[1]["balance"]) + "\n"
            place += 1
        if highscore:
            if len(highscore) < 1985:
                await self.bot.say("```py\n"+highscore+"```")
            else:
                await self.bot.say("The leaderboard is too big to be displayed. Try with a lower <top> parameter.")
        else:
            await self.bot.say("There are no accounts in the bank.")
    
    @commands.command()
    async def sleaderboard(self, top : int=10):
        """Prints out the leaderboard of special coins

        Defaults to top 10"""
        if top < 1:
            top = 10
        bank_sorted = sorted(self.bank.items(), key=lambda x: x[1]["totalsc"], reverse=True)
        if len(bank_sorted) < top:
            top = len(bank_sorted)
        topten = bank_sorted[:top]
        highscore = ""
        place = 1   
        for id in topten:
            highscore += str(place).ljust(len(str(top))+1)
            highscore += (id[1]["name"]+" ").ljust(23-len(str(id[1]["totalsc"])))
            highscore += str(id[1]["totalsc"]) + "\n"
            place += 1
        if highscore:
            if len(highscore) < 1985:
                await self.bot.say("```py\n"+highscore+"```")
            else:
                await self.bot.say("The leaderboard is too big to be displayed. Try with a lower <top> parameter.")
        else:
            await self.bot.say("There are no accounts in the bank.")

    @commands.command(pass_context=True, no_pm=True)
    async def slot(self, ctx, bid : str):
        """Play the slot machine"""
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            message = ctx.message
            bid = int(bid.replace(',', ''))
            if self.enough_money(author.id, bid):
                if bid >= self.settings["SLOT_MIN"]:
                    if author.id in self.slot_register:
                        if abs(self.slot_register[author.id] - int(time.perf_counter()))  >= self.settings["SLOT_TIME"]:         
                            if self.check_balance(message.author.id) < self.settings["MAX_BALANCE"]:
                                self.slot_register[author.id] = int(time.perf_counter())
                                await self.slot_machine(ctx.message, bid)
                            else:
                                await self.bot.say("{0} You have max coins please type !bank reset to get a special coin and you can start all over again!".format(message.author.mention))
                        else:
                            await self.bot.say("Slot machine is still cooling off! Wait {} seconds between each pull".format(self.settings["SLOT_TIME"]))
                    else:
                        if self.check_balance(message.author.id) < self.settings["MAX_BALANCE"]:
                            self.slot_register[author.id] = int(time.perf_counter())
                            await self.slot_machine(ctx.message, bid)
                        else:
                            await self.bot.say("{0} You have max coins please type !bank reset to get a special coin and you can start all over again!".format(message.author.mention))
                else:
                    await self.bot.say("{0} Bid must be between higher than {1}.".format(author.mention, self.settings["SLOT_MIN"]))
            else:
                await self.bot.say("{0} You need an account with enough funds to play the slot machine.".format(author.mention))
        else:
                    await self.bot.say("Gambling room only command")
                    
                    
                    
    async def slot_machine(self, message, bid):
        reel_pattern = [":cherries:", ":tangerine:", ":strawberry:", ":lemon:", ":grapes:", ":watermelon:", ":tomato:", ":gem:", ":seven:"]
        padding_before = [":tangerine:", ":grapes:", ":tomato:"] # padding prevents index errors
        padding_after = [":cherries:", ":lemon:", ":seven:"]
        reel = padding_before + reel_pattern + padding_after
        reels = []
        for i in range(0, 3):
            n = randint(3,12)
            reels.append([reel[n - 1], reel[n], reel[n + 1]])
        line = [reels[0][1], reels[1][1], reels[2][1]]
        
        
        for i in range(0,2):
            rand1 = randint(0,8)
            reels[i][0] = reel_pattern[rand1]
        
        for o in range(0,2):
            rand1 = randint(0,8)
            reels[i][2] = reel_pattern[rand1]
        
        
        for p in range(0,2):
            for i in range(0,8):
                rand1 = randint(1,7)
                if rand1 != 3:
                    break
                rand2 = randint(0,2)
                rand3 = randint(0,1)
                if rand3 == 0:
                    temptest = i - rand2
                    if temptest < 0:
                        temptest = 0
                    else:
                        temptest = temptest
                else:
                    temptest = i + rand2
                    if temptest > 6:
                        rand4 = randint(0,50)
                        if rand4 == 5:
                            tempest = 8
                        else:
                            rand5 = randint(0,20)
                            if rand5 == 5:
                                tempest = 7
                            else:
                                tempest = 6
                    else:
                        temptest = temptest
                reels[p][1] = reel_pattern[temptest]
        
        if reels[0][1] == reel_pattern[8]:
            rand6 = randint(1,20)
            if rand6 == 5:
                reels[0][1] = reel_pattern[8]
            else:
                rand7 = randint(0,6)
                reels[0][1] = reel_pattern[rand7]
        if reels[1][1] == reel_pattern[8]:
            rand6 = randint(1,20)
            if rand6 == 5:
                reels[1][1] = reel_pattern[8]
            else:
                rand7 = randint(0,6)
                reels[1][1] = reel_pattern[rand7]
        if reels[2][1] == reel_pattern[8]:
            rand6 = randint(1,20)
            if rand6 == 5:
                reels[2][1] = reel_pattern[8]
            else:
                rand7 = randint(0,6)
                reels[2][1] = reel_pattern[rand7]
        
        if reels[0][1] == reel_pattern[7]:
            rand6 = randint(1,10)
            if rand6 == 2:
                reels[0][1] = reel_pattern[7]
            else:
                rand7 = randint(0,6)
                reels[0][1] = reel_pattern[rand7]
        if reels[1][1] == reel_pattern[7]:
            rand6 = randint(1,10)
            if rand6 == 2:
                reels[1][1] = reel_pattern[7]
            else:
                rand7 = randint(0,6)
                reels[1][1] = reel_pattern[rand7]
        if reels[2][1] == reel_pattern[7]:
            rand6 = randint(1,10)
            if rand6 == 2:
                reels[2][1] = reel_pattern[8]
            else:
                rand7 = randint(0,6)
                reels[2][1] = reel_pattern[rand7]
        
        
        
        
        randwinchance = randint(0, 100)
        if randwinchance == 42:
            reels[1][1] = reels[0][1]
            reels[2][1] = reels[0][1]


        line[0] = reels[0][1]
        line[1] = reels[1][1]
        line[2] = reels[2][1]
        
        
        display_reels = "" + reels[0][0] + " " + reels[1][0] + " " + reels[2][0] + "\n"
        display_reels += ">" + reels[0][1] + " " + reels[1][1] + " " + reels[2][1] + "<\n"
        display_reels += "" + reels[0][2] + " " + reels[1][2] + " " + reels[2][2] + "\n"
        
        bidnow = bid
        lose = False
        
        if line[0] == ":seven:" and line[1] == ":seven:" and line[2] == ":seven:":
            bid = bid * 777
        elif line[0] == ":seven:" and line[1] == ":seven:" or line[1] == ":seven:" and line[2] == ":seven:" or line[0] == ":seven:" and line[2] == ":seven:":
            bid = bid * 77           
        elif line[0] == ":gem:" and line[1] == ":gem:" and line[2] == ":gem:":
            bid = bid * 100            
        elif line[0] == ":gem:" and line[1] == ":gem:" or line[1] == ":gem:" and line[2] == ":gem:" or line[0] == ":gem:" and line[2] == ":gem:":
            bid = bid * 25            
        elif line[0] == ":strawberry:" and line[1] == ":strawberry:" and line[2] == ":strawberry:":
            bid = bid * 20           
        elif line[0] == ":grapes:" and line[1] == ":grapes:" and line[2] == ":grapes:":
            bid = bid * 30            
        elif line[0] == ":tomato:" and line[1] == ":tomato:" and line[2] == ":tomato:":
            bid = bid * 40            
        elif line[0] == ":watermelon:" and line[1] == ":watermelon:" and line[2] == ":watermelon:":
            bid = bid * 35            
        elif line[0] == ":lemon:" and line[1] == ":lemon:" and line[2] == ":lemon:":
            bid = bid * 25            
        elif line[0] == ":tangerine:" and line[1] == ":tangerine:" and line[2] == ":tangerine:":
            bid = bid * 15            
        elif line[0] == ":cherries:" and line[1] == ":cherries:" and line[2] == ":cherries:":
            bid = bid * 10            
        elif line[0] == ":cherries:" and line[1] == ":cherries:" or line[1] == ":cherries:" and line[2] == ":cherries:" or line[0] == ":cherries:" and line[2] == ":cherries:":
            bid = bid * 5            
        elif line[0] == ":cherries:" or line[1] == ":cherries:" or line[2] == ":cherries:":
            bid = bid * 2
        else:
            lose = True

        embed = discord.Embed(type='rich', colour=discord.Colour(16776960))
        embed.add_field(name='Reel', value=display_reels, inline=False)
        embed.add_field(name='Amount Entered', value='{0:,}'.format(bidnow), inline=False)
        
        if lose:
            self.withdraw_money(message.author.id, bid)            
            embed.add_field(name='Amount Won', value='0 Coins. Better luck next time!', inline=False)
        else:
            self.add_money(message.author.id, bid)
            self.withdraw_money(message.author.id, bidnow)
            embed.add_field(name='Amount Won', value='{0:,} Coins!'.format(bid), inline=False)

        embed.add_field(name='Coin(s) Left', value='{0:,}'.format(self.check_balance(message.author.id)), inline=False)
        await self.bot.send_message(message.channel, embed=embed)
    
    
    @commands.group(name="hl", pass_context=True)
    async def _hl(self, ctx):
        """Play High/Low"""
        if ctx.message.channel.name == "gambling":
            if ctx.invoked_subcommand is None:
                pages = self.send_cmd_help(ctx)
                for page in pages:
                    await self.bot.send_message(ctx.message.channel, page)
        else:
            await self.bot.say("Gambling room only command")
    
    
    @_hl.command(pass_context=True)
    async def start(self, ctx, bid : int):
        """Play High/Low"""
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            message = ctx.message
            if self.check_fase(author.id) == 0:
                if self.enough_money(author.id, bid):
                    if bid >= self.settings["SLOT_MIN"]:
                        if author.id in self.slot_register:
                            if abs(self.slot_register[author.id] - int(time.perf_counter()))  >= self.settings["SLOT_TIME"]:         
                                if self.check_balance(message.author.id) < self.settings["MAX_BALANCE"]:
                                    self.slot_register[author.id] = int(time.perf_counter())
                                    await self.highlow(ctx.message, bid)
                                else:
                                    await self.bot.say("{0} You have max coins please type !bank reset to get a special coin and you can start all over again!".format(message.author.mention))
                            else:
                                await self.bot.say("Dealer is still busy! Wait {} seconds between each time".format(self.settings["SLOT_TIME"]))
                        else:
                            if self.check_balance(message.author.id) < self.settings["MAX_BALANCE"]:
                                self.slot_register[author.id] = int(time.perf_counter())
                                await self.highlow(ctx.message, bid)
                            else:
                                await self.bot.say("{0} You have max coins please type !bank reset to get a special coin and you can start all over again!".format(message.author.mention))
                    else:
                        await self.bot.say("{0} Bid must be between higher than {1}.".format(author.mention, self.settings["SLOT_MIN"]))
                else:
                    await self.bot.say("{0} You need an account with enough funds to play High/Low.".format(author.mention))
            else:
                await self.bot.say("{0} Please finish your game! or use !hl stop to stop the game and get your payout".format(author.mention))
        else:
            pass 
   
            
            
    async def highlow(self, message, bid):
        fase = self.check_fase(message.author.id)
        tempfase = fase + 1
        rand1 = randint(1,10)
        self.withdraw_money(message.author.id, bid)
        await self.bot.say("{} Your bid: {}. Your current number: {}. \n Your current balance: {}".format(message.author.mention, str(bid), str(rand1), str(self.check_balance(message.author.id))))
        self.set_bid(message.author.id, bid)
        self.set_card(message.author.id, rand1)
        self.set_fase(message.author.id, tempfase)
                
    
    @_hl.command(pass_context=True)
    async def high(self, ctx):
        """bet on Higher

        """
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            message = ctx.message
            if self.check_fase(author.id) > 0 and self.check_fase(author.id) < 1000:
                fase = self.check_fase(author.id)
                calc = 10
                for o in range(1,fase):
                    calc = 10 * calc
                    
                rand2 = randint(1, calc)
                rand2new = rand2*10
                currentcard = self.check_card(message.author.id)
                if rand2 > currentcard:
                    bid = self.check_bid(message.author.id)
                    if fase == 1:
                        bid = bid
                    else:
                        bid = bid * 2
                        
                    tempfase = fase + 1
                    await self.bot.say("{} You win! Your number: {}. New number: {}. \n Your bid: {}. Your current number now: {}.".format(message.author.mention, str(currentcard), str(rand2), str(bid), str(rand2new)))
                    self.set_card(message.author.id, rand2new)
                    self.set_bid(message.author.id, bid)
                    self.set_fase(message.author.id, tempfase)
                else:
                    bid = 0
                    tempfase = 0
                    self.set_fase(message.author.id, tempfase)
                    await self.bot.say("{} You lost. Your number: {}. New number: {}. \n Better luck next time! current balance: {}".format(message.author.mention, str(currentcard), str(rand2), str(self.check_balance(message.author.id))))
            else:
                await self.bot.say("{} Please start a game first with !hl start".format(message.author.mention))
        else:
            pass 
    
    @_hl.command(pass_context=True)
    async def low(self, ctx):
        """bet on Lower

        """
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            message = ctx.message
            if self.check_fase(author.id) > 0 and self.check_fase(author.id) < 1000:
                fase = self.check_fase(author.id)
                calc = 10
                for o in range(1,fase):
                    calc = 10 * calc
                    
                rand2 = randint(1, calc)
                rand2new = rand2*10
                currentcard = self.check_card(message.author.id)
                if rand2 < currentcard:
                    bid = self.check_bid(message.author.id)
                    if fase == 1:
                        bid = bid
                    else:
                        bid = bid * 2
                        
                    tempfase = fase + 1
                    await self.bot.say("{} You win! Your number: {}. New number: {}. \n Your bid: {}. Your current number now: {}.".format(message.author.mention, str(currentcard), str(rand2), str(bid), str(rand2new)))
                    self.set_card(message.author.id, rand2new)
                    self.set_bid(message.author.id, bid)
                    self.set_fase(message.author.id, tempfase)
                else:
                    bid = 0
                    tempfase = 0
                    self.set_fase(message.author.id, tempfase)
                    await self.bot.say("{} You lost. Your number: {}. New number: {}. \n Better luck next time! current balance: {}".format(message.author.mention, str(currentcard), str(rand2), str(self.check_balance(message.author.id))))
            else:
                await self.bot.say("{} Please start a game first with !hl start (bid).".format(message.author.mention))
        else:
            pass 
    
    @_hl.command(pass_context=True)
    async def stop(self, ctx):
        """Stop High/Low game and get your payout

        """
        if ctx.message.channel.name == "gambling":
            author = ctx.message.author
            message = ctx.message
            if self.check_fase(author.id) > 0 and self.check_fase(author.id) < 1000:
                bid = self.check_bid(message.author.id)
                fase = self.check_fase(author.id) - 1
                if fase == 0:
                    bid = 0
                else:
                    bid = bid
                        
                self.add_money(message.author.id, bid)
                self.set_card(message.author.id, 0)
                self.set_bid(message.author.id, 0)
                self.set_fase(message.author.id, 0)
                await self.bot.say("{} Thanks for playing, amount of bets won: {}. \n Your current balance: {}.".format(message.author.mention, str(fase), str(self.check_balance(message.author.id))))
            else:
                await self.bot.say("{} Please start a game first with !hl start (bid).".format(message.author.mention))
        else:
            pass 
                
        

    def account_check(self, id):
        if id in self.bank:
            return True
        else:
            return False

    def check_balance(self, id):
        if self.account_check(id):
            return self.bank[id]["balance"]
        else:
            return False
    
    def check_fase(self, id):
        if self.account_check(id):
            return self.bank[id]["fase"]
        else:
            return False
    
    
    
    def check_startmoney(self, id):
        if self.account_check(id):
            return self.bank[id]["startmoney"]
        else:
            return False
    
    def check_card(self, id):
        if self.account_check(id):
            return self.bank[id]["currentcard"]
        else:
            return False
    
    def check_bid(self, id):
        if self.account_check(id):
            return self.bank[id]["bid"]
        else:
            return False
    
    
            
    def check_specialbalance(self, id):
        if self.account_check(id):
            return self.bank[id]["specialcoin"]
        else:
            return False
           
    def check_specialtotalbalance(self, id):
        if self.account_check(id):
            return self.bank[id]["totalsc"]
        else:
            return False
            

    def check_marketbalance(self, id):
        marketuser = id + "market"
        if self.account_check(marketuser):
            return self.bank[marketuser]["balance"]
        else:
            return False


    def add_money(self, id, amount):
        if self.account_check(id):
            self.bank[id]["balance"] = self.bank[id]["balance"] + int(amount)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False
    
    def set_fase(self, id, amount):
        if self.account_check(id):
            self.bank[id]["fase"] = int(amount)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False
    
    def set_bid(self, id, amount):
        if self.account_check(id):
            self.bank[id]["bid"] = int(amount)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False
    
    
    
    def set_card(self, id, amount):
        if self.account_check(id):
            self.bank[id]["currentcard"] = int(amount)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False
    
    
    def set_name(self, id, name):
        if self.account_check(id):
            self.bank[id]["name"] = str(name)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False
    
    
    
    def add_sc(self, id, amount):
        if self.account_check(id):
            self.bank[id]["specialcoin"] = self.bank[id]["specialcoin"] + int(amount)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False
    
    def add_tsc(self, id, amount):
        if self.account_check(id):
            self.bank[id]["totalsc"] = self.bank[id]["totalsc"] + int(amount)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False
    
    
    
            
    def add_marketmoney(self, id, amount):
        marketuser = id + "market"
        if self.account_check(marketuser):
            self.bank[marketuser]["balance"] = self.bank[marketuser]["balance"] + int(amount)
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
        else:
            return False


    def withdraw_money(self, id, amount):
        if self.account_check(id):
            if self.bank[id]["balance"] >= int(amount):
                self.bank[id]["balance"] = self.bank[id]["balance"] - int(amount)
                files("FlandreBot/data/economy/bank.json", "save", self.bank)
            else:
                return False
        else:
            return False

    def enough_money(self, id, amount):
        if self.account_check(id):
            if self.bank[id]["balance"] >= int(amount):
                return True
            else:
                return False
        else:
            return False


    def set_money(self, id, amount):
        if self.account_check(id):
            self.bank[id]["balance"] = amount
            files("FlandreBot/data/economy/bank.json", "save", self.bank)
            return True
        else:
            return False

    def display_time(self, seconds, granularity=2): # What would I ever do without stackoverflow?
        intervals = (                               # Source: http://stackoverflow.com/a/24542445
            ('weeks', 604800),  # 60 * 60 * 24 * 7
            ('days', 86400),    # 60 * 60 * 24
            ('hours', 3600),    # 60 * 60
            ('minutes', 60),
            ('seconds', 1),
            )

        result = []

        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
        
    def checkAdmin(self, user, channel):
        return (user.permissions_in(channel).manage_server)
        
    def checkMod(self, user, channel):
        return (user.permissions_in(channel).manage_channels)
        
    def checkOwner(self, user):
        return (user.id == self.config['ownerid'])
        
    def loadConfig(self):
        ''' Load the config from the config.json file '''
        try:
            with open('FlandreBot/config.json', 'r') as config:
                self.config = json.load(config)
        except json.decoder.JSONDecodeError:
            pass
            
    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages

def check_folders():
    if not os.path.exists("FlandreBot/data/economy"):
        print("Creating data/economy folder...")
        os.makedirs("FlandreBot/data/economy")

def check_files():
    settings = {"PAYDAY_TIME" : 300, "PAYDAY_CREDITS" : 100, "SLOT_MIN" : 1, "MAX_BALANCE" : 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000, "SLOT_TIME" : 1}

    f = "FlandreBot/data/economy/settings.json"
    if not files(f, "check"):
        print("Creating default economy's settings.json...")
        files(f, "save", settings)
    else: #consistency check
        current = files(f, "load")
        if current.keys() != settings.keys():
            for key in settings.keys():
                if key not in current.keys():
                    current[key] = settings[key]
                    print("Adding " + str(key) + " field to economy settings.json")
            files(f, "save", current)

    f = "FlandreBot/data/economy/bank.json"
    if not files(f, "check"):
        print("Creating empty bank.json...")
        files(f, "save", {})

def setup(bot):
    check_folders()
    check_files()
    logger = logging.getLogger("Economy")
    if logger.level == 0: # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='FlandreBot/data/economy/Economy.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    bot.add_cog(economy(bot))
