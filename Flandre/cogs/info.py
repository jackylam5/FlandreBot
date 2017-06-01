import discord
from discord.ext import commands
from youtube_dl import version
import asyncio
from .. import permissions
import datetime

class info:

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def botinfo(self, ctx):
        ''' Shows info about the bot
        '''

        # Make server/user/voice count
        guild_count = len(self.bot.guilds)
        user_count = len(self.bot.users)
        voice_count = len(self.bot.voice_clients)
        uptime = datetime.datetime.utcnow() - self.bot.uptime
        
        # Create the embed description and embed
        desc = f'Shard Count: `{self.bot.shard_count}` Guilds: `{guild_count}` Users: `{user_count}`\nVoice Connections: `{voice_count}` Uptime: `{uptime}`'
        em = discord.Embed(type='rich', description=desc)
        em.set_author(name=f'{self.bot.user.name} Info')
        em.set_thumbnail(url=self.bot.user.avatar_url)
        
        # Add bot requirements
        em.add_field(name='Requirement Versions:', value=f'discord.py: `{discord.__version__}`\nYoutube-dl: `{version.__version__}`')
        
        # Add owners
        owner_string = ''
        for owner in self.bot.config['ownerid']:
            user = self.bot.get_user(owner)
            owner_string += f'{user.name} ({user.mention}) '
        em.add_field(name='Owners:', value=owner_string)

        # Add github link
        em.add_field(name='Github:', value='Not yet available')

        await ctx.send(embed=em)

    @commands.command()
    @commands.guild_only()
    async def guildinfo(self, ctx):
        ''' Get info about the guild 
        '''

        text_count = len(ctx.guild.text_channels)
        voice_count = len(ctx.guild.voice_channels)
        role_count = len(ctx.guild.roles)
        # Create the embed description and embed
        created = ctx.guild.created_at.strftime('%x @ %X')
        desc = f'Members: `{ctx.guild.member_count}` Text Channels: `{text_count}` Voice Channels: `{voice_count}`\nRoles: `{role_count}` Created on: `{created}`'
        em = discord.Embed(type='rich', description=desc)
        em.set_author(name=f'{ctx.guild.name} Info')
        em.set_thumbnail(url=ctx.guild.icon_url)

        # Add owner
        em.add_field(name='Owner:', value=ctx.guild.owner.mention)

        await ctx.send(embed=em)

    
    @commands.command()
    @commands.guild_only()
    async def info(self, ctx):
        ''' Get users Stats '''

        embedcolour = discord.Colour(65535)
        userembed = discord.Embed(type='rich', colour=embedcolour)
        userembed.add_field(name='Name', value=ctx.author.name)
        userembed.add_field(name='ID', value=ctx.author.id)

        # Check for nickname
        if ctx.author.nick is not None:
            userembed.add_field(name='Nickname', value=ctx.author.nick)

        userembed.add_field(name='Created', value=ctx.author.created_at.strftime('%x @ %X'))
        userembed.add_field(name='Joined', value=ctx.author.joined_at.strftime('%x @ %X'))

        # Check voice channel
        if ctx.author.voice is not None:
            userembed.add_field(name='Voice Channel', value=ctx.author.voice.channel.name)

        # Get Users roles
        roles = [role.name for role in ctx.author.roles if role.name != '@everyone']
        if roles:
            userembed.add_field(name='Roles', value=', '.join(roles), inline=False)

        # Set users avatar
        userembed.set_thumbnail(url=ctx.author.avatar_url)

        await ctx.send(embed=userembed)

    @commands.command()
    @permissions.checkOwners()
    async def guilds(self, ctx):  
        ''' Get list of servers the bot is in
        '''
        
        
        msg = '```'
        # Display all guilds with id
        for guild in self.bot.guilds:            

            if guild.voice_client is not None:
                msg += f'{guild.name} ({guild.id}) VOICE: ({guild.voice_client.channel.name}\n'
            else:
                msg += f'{guild.name} ({guild.id})\n'

            if len(msg) > 1500:
                msg += '```'
                await ctx.send(msg)
                msg = '```'
        
        msg += '```'
        await ctx.send(msg)

    @commands.command()
    @permissions.checkOwners()
    async def channels(self, ctx, guildid : int):  
        ''' Get text channels from a guild id
        '''
        
        # Get the guild
        guild = self.bot.get_guild(guildid)

        msg = f'Channels for {guild.name}:\n```'
        if guild is not None:
            # Display all channels in guild with ids
            for channel in guild.channels:
                # Check it is a text channel
                if isinstance(channel, discord.TextChannel):
                    # Check if channel is default channel
                    if channel == guild.default_channel:
                        msg += f'{channel.name} [DEFAULT] ({channel.id})\n'
                    
                    else:
                        msg += f'{channel.name} ({channel.id})\n'
                    
                    if len(msg) > 1500:
                        msg += '```'
                        await ctx.send(msg)
                        msg = '```'

            msg += '```'
            await ctx.send(msg)

        else:
            await ctx.send(f'No guild with id: `{guildid}`')

    @commands.command()
    @permissions.checkOwners()
    async def members(self, ctx, guildid : int):
        ''' Get all members of guild from guild id
        '''

        # Get the guild
        guild = self.bot.get_guild(guildid)

        msg = f'Members in {guild.name}:\n```'
        if guild is not None:
            # Display all users in guild with ids
            for member in guild.members:
                # Check it is a Bot member
                if member.bot:
                    msg += f'{member.name} [BOT] ({member.id})\n'
                
                elif member == guild.owner:
                    # Check is member is owner
                    msg += f'{member.name} [OWNER] ({member.id})\n'

                else:
                    msg += f'{member.name} ({member.id})\n'
                    
                    if len(msg) > 1500:
                        msg += '```'
                        await ctx.send(msg)
                        msg = '```'

            msg += '```'
            await ctx.send(msg)

        else:
            await ctx.send(f'No guild with id: `{guildid}`')

    @commands.command()
    @permissions.checkOwners()
    async def say(self, ctx, channelid : int, *, text : str):  
        ''' Send a message to a channel from channel id
            Use <@userid> to send a mention by getting users using member command
        '''

        # Get the channel
        channel = self.bot.get_channel(channelid)

        if channel is not None:
            await channel.send(text)
            await ctx.send(f'Message sent to {channel.name}')        

        else:
            await ctx.send(f'No channel with id: `{channelid}`')

    @commands.command(pass_context=True)
    @permissions.checkOwners()
    async def getlog(self, ctx, channelid : int, amount : int):  
        """Say something with bot in server"""
        
        
        # Get the channel
        channel = self.bot.get_channel(channelid)

        if channel is not None:
            if amount > 0:
                async for x in channel.history(limit=amount):
                    await ctx.send(f'{x.created_at} {x.author.name}: {x.content}')
                    await asyncio.sleep(0.5)
            else:
                await ctx.send('Please include amount of text bigger than 0')

        else:
            await ctx.send(f'No channel with id: `{channelid}`')
        


def setup(bot):
    n = info(bot)
    bot.add_cog(n)
