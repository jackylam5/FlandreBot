import discord
from discord.ext import commands
from .. import utils, permissions
import asyncio

class guildstuff:
    ''' Handles Guild welcome and leaving messages and custom tags
    '''

    def __init__(self, bot):
        self.bot = bot
        self.messages = utils.checkCogConfig(self, 'messages.json') # Each guild has a dict with welcome/leaving and channel all are none if not wanted (guild is removed if all is none)
        self.tags = utils.checkCogConfig(self, 'tags.json')

    def __unload(self):
        ''' Remove listeners
        '''

        self.bot.remove_listener(self.checkTag, "on_message")
        self.bot.remove_listener(self.sendWelcome, "on_member_join")
        self.bot.remove_listener(self.sendLeave, "on_member_remove")

    def checkGuildMessages(self, guild):
        ''' Check if the guild has both welcome and leaving as None if so the guild is removed from the list
        '''

        guild_messages = self.messages[str(guild.id)]
        if guild_messages['welcome'] is None and guild_messages['leave'] is None:
            del self.messages[str(guild.id)]
            self.bot.logger.info(f'{guild.name} ({guild.id}) has removed guild messages')

    def addGuildMessages(self, guild):
        ''' Add the guild to the guild messages with default messages
        '''
        
        self.messages[str(guild.id)] = {'channel': None, 'welcome': 'Welcome %user% to %server%. Enjoy your stay!', 'leave': '%user% has left the server!'}
        self.bot.logger.info(f'{guild.name} ({guild.id}) has added guild messages')

    @commands.group()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def greetings(self, ctx):
        ''' Configures leaving and welcome messages 
            It also congigures the channel they go in
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @greetings.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def channel(self, ctx):
        ''' Set the channel command is entered in as the channel for welcome and leaving messages
        '''

        removed = False
        
        # Check if guild even has guild messages
        if str(ctx.guild.id) in self.messages:
            # Check if channel is not being removed
            if ctx.channel.id == self.messages[str(ctx.guild.id)]['channel']:
                self.messages[str(ctx.guild.id)]['channel'] = None
                removed = True
            else:
                self.messages[str(ctx.guild.id)]['channel'] = ctx.channel.id

            if removed:
                await ctx.send('This channel will no longer be used as the server messages channel. Default channel will be used instead')
            else:
                await ctx.send('This channel will now be used as the server message channel')

            utils.saveCogConfig(self, 'messages.json', self.messages)
        else:
            # Add server to self.messages
            self.addGuildMessages(ctx.guild)
            self.messages[str(ctx.guild.id)]['channel'] = ctx.channel.id
            await ctx.send('This channel will now be used as the server message channel')
            utils.saveCogConfig(self, 'messages.json', self.messages)

    @greetings.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def welcome(self, ctx, *, msg : str = ''):
        ''' Set a custom welcome message. Leave blank to disable message
            %user% - places the user as a mention
            %server%/%guild% - places the server/guild name
        '''

        # Check if guild even has guild messages
        if str(ctx.guild.id) not in self.messages:
            # Add server to self.messages
            self.addGuildMessages(ctx.guild)

        if msg == '':
            self.messages[str(ctx.guild.id)]['welcome'] = None
            await ctx.send(f'{ctx.author.mention}, Welcome message has been disabled')
            self.checkGuildMessages(ctx.guild)

        else:
            self.messages[str(ctx.guild.id)]['welcome'] = msg
            await ctx.send(f'{ctx.author.mention}, Welcome message has been set to\n`{msg}`')
        
        utils.saveCogConfig(self, 'messages.json', self.messages)

    @greetings.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def leave(self, ctx, *, msg : str = ''):
        ''' Set a custom leave message. Leave blank to disable message
            %user% - places the user as a mention
            %server%/%guild% - places the server/guild name
        '''

        # Check if server even has server messages
        if str(ctx.guild.id) not in self.messages:
            # Add server to self.messages
            self.addGuildMessages(ctx.guild)

        if msg == '':
            self.messages[str(ctx.guild.id)]['leave'] = None
            await ctx.send(f'{ctx.author.mention}, Leave message has been disabled')
            self.checkGuildMessages(ctx.guild)
            
        else:
            self.messages[str(ctx.guild.id)]['leave'] = msg
            await ctx.send(f'{ctx.author.mention}, Leave message has been set to\n`{msg}`')
        
        utils.saveCogConfig(self, 'messages.json', self.messages)

    @commands.group()
    @commands.guild_only()
    async def tag(self, ctx):
        ''' Adds / Removes an custom tag that can be used by typing %<tag>
            Tags can be sentences if you want
        '''

        if ctx.invoked_subcommand is None:
            pages = await utils.sendCmdHelp(self.bot, ctx)
            for page in pages:
                await ctx.send(page)

    @tag.command()
    @commands.guild_only()
    async def view(self, ctx):
        ''' DM's you the tags the server/guild has
        '''
        
        if str(ctx.guild.id) not in self.tags:
            await ctx.send(f'{ctx.author.mention}, This server/guild has no tags')
        
        else:
            msg = f'Commands for {ctx.guild.name}\n```\n'
            for tag, resp in self.tags[str(ctx.guild.id)].items():
                if len(msg) < 1500:
                    if '\n' in resp:
                        msg += f'%{tag} : MULTILINE\n'
                    elif 'http://' in resp or 'https://' in resp:
                        msg += f'%{tag} : LINK\n'
                    else:
                        msg += f'%{tag} : {resp}\n'
                else:
                    msg += '```'
                    await ctx.author.send(msg)
                    msg = '```\n'

            msg += '```'
            await ctx.author.send(msg)
            await ctx.send(f'{ctx.author.mention}, List sent in DM')

    @tag.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def add(self, ctx, tag : str, resp : str):
        ''' Adds a custom tag to the server/guild. Make sure tag and response are in ""
            Otherwise the first word will be the tag and the second will be the response
        '''

        if str(ctx.guild.id) not in self.tags:
            self.tags[str(ctx.guild.id)] = {}
            self.bot.logger.info(f'{ctx.guild.name} ({ctx.guild.id}) has added tags')

        if tag in self.tags:
            msg = f'Edited Command: **{tag}**'
        else:
            msg = f'Added Command: **{tag}**'

        self.tags[str(ctx.guild.id)][tag] = resp
        utils.saveCogConfig(self, 'tags.json', self.tags)
        await ctx.send(msg)

    @tag.command()
    @commands.guild_only()
    @permissions.checkAdmin()
    async def remove(self, ctx, *, tag : str):
        ''' Removes a tag from the server/guild
        '''

        if str(ctx.guild.id) not in self.tags:
            await ctx.send(f'{ctx.author.mention}, This server/guild has no tags')
        
        else:
            if tag in self.tags[str(ctx.guild.id)]:
                self.tags[str(ctx.guild.id)].pop(tag, None)
                msg = f'Deleted Command: **{tag}**'
                await ctx.send(msg)
                
                if len(self.tags[str(ctx.guild.id)]) == 0:
                    del self.tags[str(ctx.guild.id)]
                    self.bot.logger.info(f'{ctx.guild.name} ({ctx.guild.id}) has removed tags')
                
                utils.saveCogConfig(self, 'tags.json', self.tags)
            else:
                await ctx.send('{0.mention}, That is not a tag in this server/guild')

    async def checkTag(self, message):
        if message.content.startswith('%') and isinstance(message.channel, discord.abc.GuildChannel):
            tag = message.content[1:]
            
            if tag in self.tags[str(message.guild.id)]:
                await message.channel.send(self.tags[str(message.guild.id)][tag])

    async def sendWelcome(self, member):
        guild = member.guild

        if str(guild.id) in self.messages:
            if self.messages[str(guild.id)]['welcome'] is not None:
                message = self.messages[str(guild.id)]['welcome']
                
                # Replace welcome message variables with data
                if '%user%' in message:
                    message = message.replace('%user%', member.mention)
                if '%server%' in message:
                    message = message.replace('%server%', guild.name)
                if '%guild%' in message:
                    message = message.replace('%guild%', guild.name)
                
                # Wait until user has fully loaded before sending message
                await asyncio.sleep(1)
                if self.messages[str(guild.id)]['channel'] is None:
                    await guild.default_channel.send(message)
                else:
                    channel = guild.get_channel(self.messages[str(guild.id)]['channel'])
                    await channel.send(message)

    async def sendLeave(self, member):
        guild = member.guild

        if str(guild.id) in self.messages:
            if self.messages[str(guild.id)]['leave'] is not None:
                message = self.messages[str(guild.id)]['leave']
                
                # Replace welcome message variables with data
                if '%user%' in message:
                    message = message.replace('%user%', member.name)
                if '%server%' in message:
                    message = message.replace('%server%', guild.name)
                if '%guild%' in message:
                    message = message.replace('%guild%', guild.name)
                
                # Wait until user has fully loaded before sending message
                await asyncio.sleep(1)
                if self.messages[str(guild.id)]['channel'] is None:
                    await guild.default_channel.send(message)
                else:
                    channel = guild.get_channel(self.messages[str(guild.id)]['channel'])
                    await channel.send(message)

def setup(bot):
    n = guildstuff(bot)
    bot.add_listener(n.checkTag, "on_message")
    bot.add_listener(n.sendWelcome, "on_member_join")
    bot.add_listener(n.sendLeave, "on_member_remove")
    bot.add_cog(n)