import discord
from discord.ext import commands
import os
from FlandreBot.utils.IO import files
from random import randint
from random import choice as randchoice
import datetime
import time
import aiohttp
import asyncio
import os
import time


class General:


    def __init__(self, bot):
        self.bot = bot
        self.poll_sessions = []

    @commands.command(pass_context=True)
    async def ping(self):
        """Pong."""
        await self.bot.say("Pong")
        
    @commands.command()
    async def choose(self, *choices):
        """Let the bot make your choice!
        """
        if len(choices) < 2:
            await self.bot.say('Not enough choices to pick from.')
        else:
            await self.bot.say(randchoice(choices))

    @commands.command(pass_context=True)
    async def roll(self, ctx, number):
        """Rolls a random number
        """
        
        author = ctx.message.author
        
        try:
            
            number = int(number)
            
            if number > 1:
                number = str(randint(1, number))
                return await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, number))
            elif number == 0 or number == 1:
                number = "1"
                return await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, number))
            else:
                number = str(randint(1, 100))
                return await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, number))
        except:
            number = str(randint(1, 100))
            return await self.bot.say("{} :game_die: {} :game_die:".format(author.mention, number))
            
    @commands.command(pass_context=True)
    async def flip(self, ctx, user : discord.Member=None):
        """ Flip a coin or user
        """
        if user != None:
            message = ""
            if user.id == self.bot.id:
                message = "Nice try but: \n"
                user = ctx.message.author
            chars = "abcdefghijklmnopqrstvwxyz"
            flippedchars = "?q?p???????l?uodb?s???x?z"
            flippedcapchars = "?q?p???HI???WNO?Q?S-n?MX?Z"
            trans = str.maketrans(chars, flippedchars)
            name = user.name.translate(trans)
            chars = chars.upper()
            trans = str.maketrans(chars, flippedcapchars)
            name = user.name.translate(trans)
            await self.bot.say(message + "(?�?�)?? " + name[::-1])
        else:
            await self.bot.say("its " + randchoice(["heads!", "tails!"]))
        
    
    @commands.command(pass_context=True)
    async def rps(self, ctx, choice : str):        
        """Play Rock Paper Scissor against the bot!
        """
        
        choices = ["rock", "paper", "scissor"]
        choice = choice.lower()
        if choice in choices:
            botchoice = randchoice(choices)
            if choice == botchoice:
                await self.bot.say("You chose: {} and the bot chose: {}, draw!".format(choice, botchoice))
            else:
                if choice == "rock" and botchoice == "scissor":
                    await self.bot.say("You chose: {} and the bot chose: {}, you win!".format(choice, botchoice))
                elif choice == "rock" and botchoice == "paper":
                    await self.bot.say("You chose: {} and the bot chose: {}, you lose :(.".format(choice, botchoice))
                elif choice == "paper" and botchoice == "rock":
                    await self.bot.say("You chose: {} and the bot chose: {}, you win :(.".format(choice, botchoice))
                elif choice == "paper" and botchoice == "scissor":
                    await self.bot.say("You chose: {} and the bot chose: {}, you lose :(.".format(choice, botchoice))
                elif choice == "scissor" and botchoice == "paper":
                    await self.bot.say("You chose: {} and the bot chose: {}, you win :(.".format(choice, botchoice))
                elif choice == "scissor" and botchoice == "rock":
                    await self.bot.say("You chose: {} and the bot chose: {}, you lose :(.".format(choice, botchoice))
        else:
            await self.bot.say("Please choose between rock, paper or scissor")
    
    @commands.command(name = "8", pass_context=True, aliases=["8ball"])
    async def _8ball(self, ctx, *question): 
        """ask 8ball a question!
        """
        
        answers = ["Yes", "No", "Maybe", "Most likely", "ask again later"]
        
        question = " ".join(question)
        if question.endswith("?") and question != "?":
            await self.bot.say("{} {}".format(ctx.message.author.mention, randchoice(answers)))
        else:
            await self.bot.say("{} please ask a question".format(ctx.message.author.mention))
    
    @commands.command()
    async def lmgtfy(self, *text):
        """links lmgtfy
        """
        
        if text == "":
            await self.bot.say("Please include search term")
        else:
            text = " ".join(text)
            await self.bot.say("http://lmgtfy.com/?q=" + text)
            
    @commands.command(pass_context=True, no_pm=True)
    async def info(self, ctx, user : discord.Member = None):
        """Shows users's informations"""
        
        if self.checkBotChannel(ctx.message.channel):
            author = ctx.message.author
            if not user:
                user = author
            roles = []
            for m in user.roles:
                if m.name != "@everyone":
                    roles.append('"' + m.name + '"') #.replace("@", "@\u200b")
            if not roles: roles = ["None"]
            data = "```python\n"
            data += "Name: " + user.name + "#{}\n".format(user.discriminator)
            data += "ID: " + user.id + "\n"
            data += "Created: " + str(user.created_at) + "\n"
            data += "Joined: " + str(user.joined_at) + "\n"
            data += "Roles: " + " ".join(roles) + "\n"
            data += "Avatar: " + user.avatar_url + "\n"
            data += "```"
            await self.bot.say(data)  
        else:
            await self.bot.say("Bot room only command")
        
    @commands.command(pass_context=True, no_pm=True)
    async def server(self, ctx):
        """Shows server's informations"""
        
        if self.checkBotChannel(ctx.message.channel):
        
            server = ctx.message.server
            online = str(len([m.status for m in server.members if str(m.status) == "online" or str(m.status) == "idle"]))
            total = str(len(server.members))
    
            data = "```\n"
            data += "Name: {}\n".format(server.name)
            data += "ID: {}\n".format(server.id)
            data += "Region: {}\n".format(str(server.region))
            data += "Users: {}/{}\n".format(online, total)
            data += "Channels: {}\n".format(str(len(server.channels)))
            data += "Roles: {}\n".format(str(len(server.roles)))
            data += "Created: {}\n".format(str(server.created_at))
            data += "Owner: {}#{}\n".format(server.owner.name, server.owner.discriminator)
            data += "Icon: {}\n".format(server.icon_url)
            data += "```"
            await self.bot.say(data)
        else:
            await self.bot.say("Bot room only command")
        
    @commands.command()
    async def urban(self, *, search_terms : str):
        """Urban Dictionary search"""
        search_terms = search_terms.split(" ")
        search_terms = "+".join(search_terms)
        search = "http://api.urbandictionary.com/v0/define?term=" + search_terms
        try:
            async with aiohttp.get(search) as r:
                result = await r.json()
            if result["list"] != []:
                definition = result['list'][0]['definition']
                example = result['list'][0]['example']
                await self.bot.say("**Definition:** " + definition + "\n\n" + "**Example:** " + example )
            else:
                await self.bot.say("Your search terms gave no results.")
        except:
            await self.bot.say("Error.")
            
    @commands.command(pass_context=True, no_pm=True)
    async def poll(self, ctx, *text):
        """Starts/stops a poll

        Usage example:
        poll Is this a poll?;Yes;No;Maybe
        poll stop"""
        message = ctx.message
        if len(text) == 1:
            if text[0].lower() == "stop":
                await self.endpoll(message)
                return
        if not self.getPollByChannel(message):
            check = " ".join(text).lower()
            if "@everyone" in check or "@here" in check:
                await self.bot.say("Nice try.")
                return
            p = NewPoll(message, self)
            if p.valid:
                self.poll_sessions.append(p)
                await p.start()
            else:
                await self.bot.say("poll question;option1;option2 (...)")
        else:
            await self.bot.say("A poll is already ongoing in this channel.")

    async def endpoll(self, message):
        if self.getPollByChannel(message):
            p = self.getPollByChannel(message)
            if p.author == message.author.id: # or isMemberAdmin(message)
                await self.getPollByChannel(message).endPoll()
            else:
                await self.bot.say("Only admins and the author can stop the poll.")
        else:
            await self.bot.say("There's no poll ongoing in this channel.")

    def getPollByChannel(self, message):
        for poll in self.poll_sessions:
            if poll.channel == message.channel:
                return poll
        return False

    async def check_poll_votes(self, message):
        if message.author.id != self.bot.user.id:
            if self.getPollByChannel(message):
                    self.getPollByChannel(message).checkAnswer(message)

    def checkBotChannel(self, channel):
        if "bot" in channel.name:
            return True
        else:
            return False

class NewPoll():
    def __init__(self, message, main):
        self.channel = message.channel
        self.author = message.author.id
        self.client = main.bot
        self.poll_sessions = main.poll_sessions
        msg = message.content[6:]
        msg = msg.split(";")
        if len(msg) < 2: # Needs at least one question and 2 choices
            self.valid = False
            return None
        else:
            self.valid = True
        self.already_voted = []
        self.question = msg[0]
        msg.remove(self.question)
        self.answers = {}
        i = 1
        for answer in msg: # {id : {answer, votes}}
            self.answers[i] = {"ANSWER" : answer, "VOTES" : 0}
            i += 1

    async def start(self):
        msg = "**POLL STARTED!**\n\n{}\n\n".format(self.question)
        for id, data in self.answers.items():
            msg += "{}. *{}*\n".format(id, data["ANSWER"])
        msg += "\nType the number to vote!"
        await self.client.send_message(self.channel, msg)
        await asyncio.sleep(30)
        if self.valid:
            await self.endPoll()

    async def endPoll(self):
        self.valid = False
        msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
        for data in self.answers.values():
            msg += "*{}* - {} votes\n".format(data["ANSWER"], str(data["VOTES"]))
        await self.client.send_message(self.channel, msg)
        self.poll_sessions.remove(self)

    def checkAnswer(self, message):
        try:
            i = int(message.content)
            if i in self.answers.keys():
                if message.author.id not in self.already_voted:
                    data = self.answers[i]
                    data["VOTES"] += 1
                    self.answers[i] = data
                    self.already_voted.append(message.author.id)
        except ValueError:
            pass
        
        
def check_folders():
    if not os.path.exists("FlandreBot/data/general"):
        print("Creating FlandreBot/data/general folder...")
        os.makedirs("FlandreBot/data/general")

def setup(bot):
    check_folders()
    n = General(bot)
    bot.add_cog(n)
