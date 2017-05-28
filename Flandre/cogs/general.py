import discord
from discord.ext import commands
from random import choice, randint
from urllib.parse import quote
import aiohttp
import asyncio
from .. import utils

class general:
    '''Holds commands that don't have a suitable place else where'''
    def __init__(self, bot):
        self.bot = bot
        self.polls = {}

    def __unload(self):
        ''' Remove listeners
        '''

        self.bot.remove_listener(self.check_poll_votes, "on_message")

    @commands.command(hidden=True)
    async def ping(self, ctx):
        ''' Pong '''
        
        await ctx.send('Pong')

    @commands.command()
    async def roll(self, ctx, *number : str):
        '''Rolls an random number from your choice. 
        If none supplied defaults to 100
        '''

        try:
            # Try convert to an integer
            number = int(number[0])
            rand = randint(0, number)
            
        except:
            rand = randint(0, 100)
        
        finally:
            await ctx.send(f"{ctx.author.mention} you rolled :game_die: {rand}")

    @commands.command()
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
                
            await ctx.send(f"You chose: {userchoice} and the bot chose: {botchoice}. {result}")
        else:
            await ctx.send("Please choose between rock, paper or scissor")

    @commands.command(name = "8", aliases=["8ball"])
    async def _8ball(self, ctx, *question : str): 
        '''Ask 8ball a question!
        '''
        
        answers = ["Yes", "No", "Maybe", "Most likely", "Ask again later"]
        
        if question[-1].endswith('?') and not question[0].startswith('?'):
            answer = choice(answers)
            await self.bot.say(f"{ctx.author.mention}, {answer}")
        else:
            await self.bot.say(f"{ctx.author.mention}, Please ask a question")

    @commands.command()
    async def choose(self, ctx, *choices):
        '''Make the bot choose for you. Each word is a choice
        '''

        if len(choices) < 2:
            await ctx.send('Not really letting me choose are you')
        else:
            picked = choice(choices)
            em = discord.Embed(type='rich', description=picked)
            await ctx.send(embed=em)

    @commands.command()
    async def lmgtfy(self, ctx, *, text: str):
        '''Does a lmgtfy 
        '''
        
        if text:
            text = quote(text)
            await ctx.send(f"http://lmgtfy.com/?q={text}")
        else:
            await ctx.send(f"{ctx.author.mention}, Please include search term")

    @commands.command()
    async def urban(self, ctx, *, search_terms : str):
        '''Urban Dictionary search
        '''
        if search_terms:
            search = "http://api.urbandictionary.com/v0/define?term=" + quote(search_terms)
            
            with aiohttp.ClientSession() as aioclient:
                async with aioclient.get(search) as resp:
                    status_code = resp.status
                    data = await resp.json()
            
            if status_code == 200:
                if data["list"]:
                    em = discord.Embed(type='rich')
                    em.set_author(name='Urban')
                    em.add_field(name='Definition:', value=data['list'][0]['definition'])
                    em.add_field(name='Example:', value=data['list'][0]['example'])
                    await ctx.send(embed=em)
                else:
                    await ctx.send(f"{ctx.author.mention}, Your search terms gave no results.")
            else:
                await self.bot.say(f"{ctx.author.mention}, Error. It seems the Urban Dictionary API is down. Status Code:{status_code}")
        else:
            await ctx.send(f"{ctx.author.mention}, You didn't search for anything")

    @commands.group()
    @commands.guild_only()
    async def poll(self, ctx):
        ''' Poll commands
            Start and stop a poll
        '''
        
        if ctx.invoked_subcommand is None:
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @poll.command()
    @commands.guild_only()
    async def start(self, ctx, *, text : str):
        
        '''
        Starts a poll format Is this a poll?;Yes;No;Maybe
        '''
        if ctx.channel.id not in self.polls:
            check = " ".join(text).lower()
            # Make sure everyone isn't mentioned
            if "@everyone" in check or "@here" in check:
                await ctx.send("Nice try.")
            else:
                # Create Poll
                p = Poll(ctx.message, text, self)
                if p.valid:
                    self.polls[ctx.channel.id] = p
                    self.bot.logger.info(f"New Poll made in channel: {ctx.channel.id}")
                    await p.start()
                else:
                    await ctx.send("poll question;option1;option2 (...)")
        else:
            await ctx.send("A poll is already ongoing in this channel.")

    @poll.command()
    @commands.guild_only()
    async def stop(self, ctx):
        '''
        Stops the poll
        '''
        if ctx.channel.id in self.polls:
            p = self.polls[ctx.channel.id]
            if p.author == ctx.author.id:
                await p.endPoll()
                del p
            else:
                await ctx.send("Only the author can stop the poll.")
        else:
            await ctx.send("There's no poll ongoing in this channel.")

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

    def __init__(self, message, text, cog):
        self.channel = message.channel
        self.author = message.author.id
        self.cog = cog
        msg = text.split(";")
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
        msg = f"**POLL STARTED!**\n\n{self.question}\n\n"
        for id, data in self.answers.items():
            answer = data['ANSWER']
            msg += f"{id}. {answer}\n"
        msg += "\nType the number to vote!"
        em = discord.Embed(type='rich', description=msg)
        em.set_author(name='Poll')
        await self.channel.send(embed=em)
        await asyncio.sleep(30)
        if self.valid:
            await self.endPoll()

    async def endPoll(self):
        self.valid = False
        msg = f"**POLL ENDED!**\n\n{self.question}\n\n"
        for data in self.answers.values():
            answer = data['ANSWER']
            votes = data['VOTES']
            msg += f"{answer} - {votes} votes\n"
        em = discord.Embed(type='rich', description=msg)
        em.set_author(name='Poll')
        await self.channel.send(embed=em)
        self.cog.remove_poll(self.channel.id)
        self.cog.bot.logger.info(f"Poll deleted for channel: {self.channel.id}")

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