''' Holds the general cog '''
import asyncio
from random import choice, randint
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands

from .. import utils

numberReactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣']


class General:
    ''' Holds commands that don't have a suitable place else where '''
    def __init__(self, bot):
        self.bot = bot
        self.polls = {}

    def __unload(self):
        ''' Remove listeners '''
    
    async def __local_check(self, ctx):
        return utils.check_enabled(ctx)

    @commands.command(hidden=True)
    async def ping(self, ctx):
        ''' Pong '''

        await ctx.send('Pong')

    @commands.command(hidden=True)
    async def reacttest(self, ctx):
        ''' Pong '''
        
        await ctx.send('test')    
        lastMessage = await self.getLastMessage(ctx.message.channel)
        #for number in numberReactions:
        #    await lastMessage.add_reaction(number)
        await lastMessage.add_reaction('9⃣')
        lastMessage = await self.getLastMessage(ctx.message.channel)
        list = lastMessage.reactions
        print(list)

            
    @commands.command()
    async def roll(self, ctx, *number: str):
        '''
        Rolls a random number from your choice.
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
    async def rps(self, ctx, userchoice: str):
        ''' Play Rock Paper Scissor against the bot! '''

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

    @commands.command(name="8", aliases=["8ball"])
    async def _8ball(self, ctx, *question: str):
        ''' Ask 8ball a question! '''

        answers = ["Yes", "No", "Maybe", "Most likely", "Ask again later"]

        if question[-1].endswith('?') and not question[0].startswith('?'):
            answer = choice(answers)
            await ctx.send(f"{ctx.author.mention}, {answer}")
        else:
            await ctx.send(f"{ctx.author.mention}, Please ask a question")

    @commands.command()
    async def choose(self, ctx, *choices):
        ''' Make the bot choose for you. Each word is a choice '''

        if len(choices) < 2:
            await ctx.send('Not really letting me choose are you')
        else:
            picked = choice(choices)
            embed = discord.Embed(type='rich', description=picked)
            await ctx.send(embed=embed)

    @commands.command()
    async def lmgtfy(self, ctx, *, text: str):
        ''' Does a lmgtfy '''

        if text:
            text = quote(text)
            url = f"http://lmgtfy.com/?q={text}"

            if len(url) > 1999:
                url = url[:1999]
            await ctx.send(url)
        else:
            await ctx.send(f"{ctx.author.mention}, Please include search term")

    @commands.command()
    async def urban(self, ctx, *, search_terms: str):
        ''' Urban Dictionary search '''
        if search_terms:
            search = "http://api.urbandictionary.com/v0/define?term=" + quote(search_terms)

            async with aiohttp.ClientSession() as aioclient:
                async with aioclient.get(search) as resp:
                    status_code = resp.status
                    data = await resp.json()

            if status_code == 200:
                if data["list"]:
                    embed = discord.Embed(type='rich')
                    embed.set_author(name='Urban')
                    embed.add_field(name='Definition:', value=data['list'][0]['definition'])
                    embed.add_field(name='Example:', value=data['list'][0]['example'])
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"{ctx.author.mention}, Your search terms gave no results.")
            else:
                await self.bot.say((f"{ctx.author.mention}, Error. "
                                    "It seems the Urban Dictionary API is down. "
                                    f"Status Code:{status_code}"))
        else:
            await ctx.send(f"{ctx.author.mention}, You didn't search for anything")

    @commands.group()
    @commands.guild_only()
    async def poll(self, ctx):
        '''
        Poll commands
        Start and stop a poll
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.send_cmd_help(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @poll.command()
    @commands.guild_only()
    async def start(self, ctx, *, text: str):

        '''
        Starts a poll format Is this a poll?;Yes;No;Maybe
        '''
        if ctx.message.author.id not in self.polls:
            check = " ".join(text).lower()
            # Make sure everyone isn't mentioned
            if "@everyone" in check or "@here" in check:
                await ctx.send("Nice try.")
            else:
                # Create Poll
                poll = Poll(ctx.message, text, self, self.bot)
                if poll.valid:
                    self.polls[ctx.message.author.id] = poll
                    self.bot.logger.info(f"New Poll made in channel: {ctx.channel.id}")
                    await poll.start()
                else:
                    await ctx.send("poll question;option1;option2 (...)")
        else:
            await ctx.send("You already started a poll.")

    @poll.command()
    @commands.guild_only()
    async def stop(self, ctx):
        '''
        Stops the poll
        '''
        if ctx.message.author.id in self.polls:
            poll = self.polls[ctx.message.author.id]
            await poll.end_poll()
            del poll
        else:
            await ctx.send("There's no poll ongoing in this channel.")

    def remove_poll(self, pid):
        ''' Removes the poll '''
        self.polls.pop(pid)
        
    async def getLastMessage(self, channel):
        async for message in channel.history(limit=10):
            if message.author.id == self.bot.user.id:
                print('a')
                return message

class Poll():
    ''' Poll Class
    Holds the poll for the channel it was started in
    '''

    def __init__(self, message, text, cog, bot):
        self.channel = message.channel
        self.author = message.author.id
        self.cog = cog
        self.bot = bot
        self.messageID = None
        msg = text.split(";")
        if len(msg) < 2 or len(msg) > 10: # Needs at least one question and 2 choices
            self.valid = False
            return None
        else:
            self.valid = True
        self.question = msg[0]
        msg.remove(self.question)
        self.answers = {}
        i = 1
        for answer in msg: # {id : {answer, votes}}
            self.answers[i] = {"ANSWER" : answer}
            i += 1

    async def start(self):
        ''' Used to start the poll '''
        msg = f"**POLL STARTED!**\n\n{self.question}\n\n"
        for pid, data in self.answers.items():
            answer = data['ANSWER']
            msg += f"{pid}. {answer}\n"
        msg += "\nReact to vote!"
        embed = discord.Embed(type='rich', description=msg)
        embed.set_author(name='Poll')
        await self.channel.send(embed=embed)
        lastMessage = await self.getLastMessage(self.bot, self.channel)
        self.messageID = lastMessage.id
        for x in range(len(self.answers.items())):
            await lastMessage.add_reaction(numberReactions[x])
        try:
            lastMessage = await self.channel.get_message(self.messageID)
            await lastMessage.pin()
        except:
            print('something went wrong')

    async def end_poll(self):
        ''' Used to end the poll '''
        self.valid = False
        msg = f"**POLL ENDED!**\n\n{self.question}\n\n"
        lastMessage = await self.channel.get_message(self.messageID)
        reactions = lastMessage.reactions
        print(len(reactions))
        for pid, data in self.answers.items():
            answer = data['ANSWER']
            votes = reactions[pid-1].count - 1
            msg += f"{answer} - {votes} votes\n"
        embed = discord.Embed(type='rich', description=msg)
        embed.set_author(name='Poll')
        await self.channel.send(embed=embed)
        self.cog.remove_poll(self.author)
        self.cog.bot.logger.info(f"Poll deleted for channel: {self.channel.id}")
        try:
            await lastMessage.unpin()
        except:
            pass

    async def getLastMessage(self, bot, channel):
        async for message in channel.history(limit=10):
            if message.author.id == bot.user.id:
                return message

def setup(bot):
    ''' Setup function to add cog to bot '''
    cog = General(bot)
    bot.add_cog(cog)
