''' Holds the info cog for the bot '''
import asyncio

import discord
from discord.ext import commands
from youtube_dl import version

from .. import permissions, utils


class Info(commands.Cog):
    '''
    Info cog holds info about bot
    Also can show guild and user info
    '''

    def __init__(self, bot):
        self.bot = bot
        self.past_names = utils.check_cog_config(self, 'past_names.json')

    #def __unload(self):
    #    ''' Remove listeners '''

    #    self.bot.remove_listener(self.check_names, "on_member_update")

    async def __local_check(self, ctx):
        return utils.check_enabled(ctx)

    @commands.command()
    async def botinfo(self, ctx):
        ''' Shows info about the bot
        '''

        # Make server/user/voice count
        guild_count = len(self.bot.guilds)
        user_count = len(self.bot.users)
        voice_count = len(self.bot.voice_clients)

        # Create the embed description and embed
        desc = (f'Shard Count: `{self.bot.shard_count}` '
                f'Guilds: `{guild_count}` '
                f'Users: `{user_count}`\n'
                f'Voice Connections: `{voice_count}` '
                f'Uptime: `{self.bot.uptime}`')

        embed = discord.Embed(type='rich', description=desc)
        embed.set_author(name=f'{self.bot.user.name} Info')
        embed.set_thumbnail(url=self.bot.user.avatar_url)

        # Add bot requirements
        req_msg = f'discord.py: `{discord.__version__}`\nYoutube-dl: `{version.__version__}`'
        embed.add_field(name='Requirement Versions:', value=req_msg)

        # Add owners
        owner_string = ''
        for owner in self.bot.config['ownerid']:
            user = self.bot.get_user(owner)
            owner_string += f'{user.name} ({user.mention}) '
        embed.add_field(name='Owners:', value=owner_string)

        # Add github link
        embed.add_field(name='Github:', value='Not yet available')

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def guildinfo(self, ctx):
        ''' Get info about the guild '''

        text_count = len(ctx.guild.text_channels)
        voice_count = len(ctx.guild.voice_channels)
        role_count = len(ctx.guild.roles)
        # Create the embed description and embed
        created = ctx.guild.created_at.strftime('%x @ %X')
        desc = (f'Members: `{ctx.guild.member_count}` '
                f'Text Channels: `{text_count}` '
                f'Voice Channels: `{voice_count}`\n'
                f'Roles: `{role_count}` '
                f'Created on: `{created}`')

        embed = discord.Embed(type='rich', description=desc)
        embed.set_author(name=f'{ctx.guild.name} Info')
        embed.set_thumbnail(url=ctx.guild.icon_url)

        # Add owner
        embed.add_field(name='Owner:', value=ctx.guild.owner.mention)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def info(self, ctx, member: discord.Member=None):
        ''' Get users Stats '''

        # Check if a user was mentioned
        if member is None:
            member = ctx.author

        embedcolour = discord.Colour(65535)
        userembed = discord.Embed(type='rich', colour=embedcolour)
        userembed.add_field(name='Name', value=member.name)
        userembed.add_field(name='ID', value=member.id)

        # Check for nickname
        if member.nick is not None:
            userembed.add_field(name='Nickname', value=member.nick)

        userembed.add_field(name='Created', value=member.created_at.strftime('%x @ %X'))
        userembed.add_field(name='Joined', value=member.joined_at.strftime('%x @ %X'))

        # Check voice channel
        if member.voice is not None:
            userembed.add_field(name='Voice Channel', value=member.voice.channel.name)

        # Get Users roles
        roles = [role.name for role in member.roles if role.name != '@everyone']
        if roles:
            userembed.add_field(name='Roles', value=', '.join(roles), inline=False)

        # Get past names
        if str(member.id) in self.past_names:
            names = ', '.join(self.past_names[str(member.id)])
            userembed.add_field(name='Past names', value=names, inline=False)

        # Set users avatar
        userembed.set_thumbnail(url=member.avatar_url)

        await ctx.send(embed=userembed)

    @commands.command()
    @permissions.check_owners()
    async def guilds(self, ctx):
        ''' Get list of servers the bot is in '''

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
    @permissions.check_owners()
    async def channels(self, ctx, guildid: int):
        ''' Get text channels from a guild id '''

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
    @permissions.check_owners()
    async def members(self, ctx, guildid: int):
        ''' Get all members of guild from guild id '''

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
    @permissions.check_owners()
    async def say(self, ctx, channelid: int, *, text: str):
        '''
        Send a message to a channel from channel id
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
    @permissions.check_owners()
    async def getlog(self, ctx, channelid: int, amount: int):
        ''' Say something with bot in server '''

        # Get the channel
        channel = self.bot.get_channel(channelid)

        if channel is not None:
            if amount > 0:
                async for msg in channel.history(limit=amount):
                    await ctx.send(f'{msg.created_at} {msg.author.name}: {msg.content}')
                    await asyncio.sleep(0.5)
            else:
                await ctx.send('Please include amount of text bigger than 0')

        else:
            await ctx.send(f'No channel with id: `{channelid}`')

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        ''' Listener to check the users past names'''
        if before.name != after.name:
            if str(before.id) not in self.past_names.keys():
                self.past_names[str(before.id)] = [before.name]
            else:
                if before.name not in self.past_names[str(before.id)]:
                    # If there are 5 or more names remove the oldest one
                    if len(self.past_names[str(before.id)]) >= 5:
                        self.past_names[str(before.id)].pop()
                    self.past_names[str(before.id)].append(before.name)

            utils.save_cog_config(self, 'past_names.json', self.past_names)

def setup(bot):
    ''' Add the cog to the bot '''
    cog = Info(bot)
    bot.add_listener(cog.on_member_update, "on_member_update")
    bot.add_cog(cog)
