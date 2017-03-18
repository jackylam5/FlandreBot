import discord
from discord.ext import commands
from random import choice, randint
import upsidedown
import aiohttp
import asyncio

class general:
    '''Holds commands that don't have a suitable place else where'''

    def __init__(self, bot):
        self.bot = bot
        self.polls = {}

    @commands.command()
    async def ping(self):
        ''' Pong '''
        
        await self.bot.say("pong")

    @commands.command()
    async def choose(self, *choices):
        '''Make the bot choose for you. Each word is a choice
        '''

        if len(choices) < 2:
            await self.bot.say('Not really letting me choose are you')
        else:
            await self.bot.say(choice(choices))

    @commands.command(pass_context=True)
    async def roll(self, ctx, *number):
        '''Rolls an random number from your choice. 
        If none supplied defaults to 100
        '''

        try:
            # Try convert to an integer
            number = int(number[0])
            await self.bot.say("{0} you rolled :game_die: {1}".format(ctx.message.author.mention, randint(0,number)))
        except:
            await self.bot.say("{0} you rolled :game_die: {1}".format(ctx.message.author.mention, randint(0,100)))

    @commands.command(pass_context=True)
    async def flip(self, ctx, user=None):
        ''' Flip a coin or the mentioned user
        '''

        # Check if user was mentioned
        if ctx.message.mentions:
            user = ctx.message.mentions[0]

        if user != None and isinstance(user, discord.Member):
            message = ''
            if user.id == self.bot.user.id:
                message = "Nice try but: \n"
                user = ctx.message.author
            flipped = upsidedown.transform(user.display_name)
            await self.bot.say("{0}(╯°□°）╯︵ {1}".format(message, flipped))
        else:
            await self.bot.say("It's " + choice(["heads!", "tails!"]))

    @commands.command(pass_context=True)
    async def rps(self, ctx, userchoice : str):
        '''Play Rock Paper Scissor against the bot!
        '''

        choices = ["rock", "paper", "scissor"]
        userchoice = userchoice.lower()

        # Check is valid choice
        if userchoice in choices:
            # Make bot choose
            botchoice = choice(choices)
                
            # Check result
            result = ''
            if userchoice == "rock" and botchoice == "scissor":
                result = 'You Win!'
            elif userchoice == "rock" and botchoice == "paper":
                result = 'You Lose :frowning:'
            elif userchoice == "paper" and botchoice == "rock":
                result = 'You Win!'
            elif userchoice == "paper" and botchoice == "scissor":
                result = 'You Lose :frowning:'
            elif userchoice == "scissor" and botchoice == "paper":
                result = 'You Win!'
            elif userchoice == "scissor" and botchoice == "rock":
                result = 'You Lose :frowning:'
            elif userchoice == botchoice:
                result = "It's a draw!"
                
            await self.bot.say("You chose: {0} and the bot chose: {1}. {2}".format(userchoice, botchoice, result))
        else:
            await self.bot.say("Please choose between rock, paper or scissor")

    @commands.command(name = "8", pass_context=True, aliases=["8ball"])
    async def _8ball(self, ctx, *question): 
        '''Ask 8ball a question!
        '''
        
        answers = ["Yes", "No", "Maybe", "Most likely", "Ask again later"]
        
        if question[-1].endswith('?') and not question[0].startswith('?'):
            await self.bot.say("{0}, {1}".format(ctx.message.author.mention, choice(answers)))
        else:
            await self.bot.say("{0}, Please ask a question".format(ctx.message.author.mention))

    @commands.command(pass_context=True)
    async def lmgtfy(self, ctx, *text):
        '''Does a lmgtfy 
        '''
        
        if text:
            await self.bot.say("http://lmgtfy.com/?q={0}".format("+".join(text)))
        else:
            await self.bot.say("{0}, Please include search term".format(ctx.message.author.mention))

    @commands.command(pass_context=True)
    async def urban(self, ctx, *search_terms):
        '''Urban Dictionary search
        '''
        if search_terms:
            search_terms = "+".join(search_terms)
            search = "http://api.urbandictionary.com/v0/define?term=" + search_terms
            
            with aiohttp.ClientSession() as aioclient:
                async with aioclient.get(search) as resp:
                    status_code = resp.status
                    data = await resp.json()
            
            if status_code == 200:
                if data["list"]:
                    definition = data['list'][0]['definition']
                    example = data['list'][0]['example']
                    await self.bot.say("**Definition:** {0}\n\n**Example:** {1}".format(definition, example))
                else:
                    await self.bot.say("{0}, Your search terms gave no results.".format(ctx.message.author.mention))
            else:
                await self.bot.say("{0}, Error. It seems the Urban Dictionary API is down. Status Code:{1}".format(ctx.message.author.mention, status_code))
        else:
            await self.bot.say("{0}, You didn't search for anything".format(ctx.message.author.mention))

    @commands.command(pass_context=True, no_pm=True)
    async def poll(self, ctx, *text):
        '''Starts/stops a poll

        Usage example:
        poll Is this a poll?;Yes;No;Maybe
        poll stop
        '''
        message = ctx.message
        
        if len(text) == 1:
            if text[0].lower() == "stop":
                # Stop the poll
                if message.channel.id in self.polls:
                    p = self.polls[message.channel.id]
                    if p.author == message.author.id:
                        await p.endPoll()
                        del p
                    else:
                        await self.bot.say("Only admins and the author can stop the poll.")
                else:
                    await self.bot.say("There's no poll ongoing in this channel.")
                return

        if message.channel.id not in self.polls:
            check = " ".join(text).lower()
            # Make sure everyone isn't mentioned
            if "@everyone" in check or "@here" in check:
                await self.bot.say("Nice try.")
            else:
                # Create Poll
                p = Poll(message, self)
                if p.valid:
                    self.polls[message.channel.id] = p
                    self.bot.log('info', "New Poll made in channel: {0}".format(message.channel.id))
                    await p.start()
                else:
                    await self.bot.say("poll question;option1;option2 (...)")
        else:
            await self.bot.say("A poll is already ongoing in this channel.")

    async def check_poll_votes(self, message):
        if message.author.id != self.bot.user.id:
            if message.channel.id in self.polls:
                self.polls[message.channel.id].checkAnswer(message)

    def remove_poll(self, id):
        self.polls.pop(id)


class Poll():
    ''' Poll Class
    Holds the poll for the channel it was started in
    '''

    def __init__(self, message, cog):
        self.channel = message.channel
        self.author = message.author.id
        self.cog = cog
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
        await self.cog.bot.send_message(self.channel, msg)
        await asyncio.sleep(30)
        if self.valid:
            await self.endPoll()

    async def endPoll(self):
        self.valid = False
        msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
        for data in self.answers.values():
            msg += "*{}* - {} votes\n".format(data["ANSWER"], str(data["VOTES"]))
        await self.cog.bot.send_message(self.channel, msg)
        self.cog.remove_poll(self.channel.id)
        self.cog.bot.log('info', "Poll deleted for channel: {0}".format(self.channel.id))

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

def setup(bot):
    n = general(bot)
    bot.add_listener(n.check_poll_votes, "on_message")
    bot.add_cog(n)