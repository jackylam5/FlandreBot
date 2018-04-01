''' A cog for Flandre made for the programming guild '''
import asyncio
import datetime

import discord
from discord.ext import commands

from .. import permissions, utils

# The id for the guild. This is used to check that only that guild can use the cog
GUILD_ID =
BOT_CHANNEL_ID =
JOIN_CHANNEL_ID =
REPORT_CHANNEL_ID =

def check_server():
    '''
    The check function to make sure the guild is the one
    set with the GUILD_ID variable
    '''

    def check(ctx):
        ''' The actual check '''
        return ctx.guild.id == GUILD_ID

    return commands.check(check)

class Programming:
    '''
    The cog for the programming guild.
    It handles the accept command that gives the member role.
    And the join/leave role command which gives the users the roles
    they ask for it has been set up
    '''

    def __init__(self, bot):
        self.bot = bot
        self.roles = utils.check_cog_config(self, 'roles.json', default={'roles': []})
        self.role_check = self.bot.loop.create_task(self.role_checker())

    def __unload(self):
        ''' Remove listeners '''

        self.bot.remove_listener(self.join_server, "on_member_join")
        self.role_check.cancel()

    def get_givable_roles(self, guild):
        '''
        Gets the roles the bot can give to other users
        '''

        top_role = guild.me.top_role
        giveable_roles = {}

        # The variable that tell the loop to start adding to the giveable roles list
        highest_role_found = False

        for role in guild.role_hierarchy:
            if role.name.lower() == top_role.name.lower():
                highest_role_found = True
            elif highest_role_found:
                giveable_roles[role.name.lower()] = role
            else:
                continue

        return giveable_roles

    @commands.command()
    @commands.guild_only()
    @check_server()
    async def agree(self, ctx):
        ''' Used to give user the member role if they agree to the rules '''

        if ctx.channel.id != JOIN_CHANNEL_ID:
            return

        guest_role = discord.utils.get(ctx.guild.roles, name='Guest')
        member_role = discord.utils.get(ctx.guild.roles, name='Member')

        if guest_role is None or member_role is None:
            return

        if guest_role not in ctx.author.roles:
            return

        await ctx.author.remove_roles(guest_role)
        await ctx.author.add_roles(member_role)
        await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    @check_server()
    async def prune(self, ctx, days: int = 14):
        '''
        Removes all guests that have been on the server for more than X days
        The age is 14 days, or 2 weeks
        '''

        guest_role = discord.utils.get(ctx.guild.roles, name='Guest')

        if guest_role is None:
            return

        prune_date = datetime.datetime.now() - datetime.timedelta(days=days)

        def prune_filter(member):
            if len(member.roles) == 2:
                if guest_role in member.roles:
                    if member.joined_at < prune_date:
                        return True
            return False

        to_be_pruned = filter(prune_filter, ctx.guild.members)
        for member in to_be_pruned:
            await ctx.guild.kick(member, f'Pruning guests older than {days} days')

        guild_id = str(ctx.guild.id)
        if guild_id in self.logging_channels:
            log_channel = self.bot.get_channel(self.logging_channels[guild_id])
            timestamp = ctx.message.created_at
            desc = f'Pruned {len(to_be_pruned)} guests older than {days} days.'
            embed = discord.Embed(type='rich', description=desc, timestamp=timestamp)
            embed.set_author(name='Prune Log')
            embed.set_footer(text=f'Done by {ctx.author.name}', icon_url=ctx.author.avatar_url)
            await log_channel.send(embed=embed)

    @commands.group()
    @commands.guild_only()
    @check_server()
    async def role(self, ctx):
        '''
        The role command used to join/leave roles
        It also will allow admins it add roles to the list that have been premade
        So users can join them with the command
        '''

        if ctx.channel.id == BOT_CHANNEL_ID:
            if ctx.invoked_subcommand is None:
                pages = await utils.send_cmd_help(self.bot, ctx)
                for page in pages:
                    await ctx.send(page)

    @role.command()
    @commands.guild_only()
    @check_server()
    async def show(self, ctx):
        '''
        Show the roles the user can get in DM.
        If DM fails it is posted in the channel then deleted after 20 seconds
        '''

        if ctx.channel.id == BOT_CHANNEL_ID:
            message = '```css\n'
            for role in sorted(self.roles['roles']):
                message += f'{role}\n'
        message += '```'
        try:
            await ctx.message.author.send(message)
            await ctx.send('{}, Please check DM for list of roles'.format(ctx.author.mention))
        except:
            await ctx.send(f'{message}\nThis will delete after 20 seconds', delete_after=20)

    @role.command()
    @commands.guild_only()
    @check_server()
    @permissions.check_admin()
    async def add(self, ctx, *, role: str):
        '''
        Add a role already set up on the guild to the list.
        So users can use the bot to get the role
        '''

        if ctx.channel.id == BOT_CHANNEL_ID:
            # Get the roles the bot can give in the guild
            giveable_roles = self.get_givable_roles(ctx.guild)

            if role.lower() in giveable_roles:
                if role.lower() in self.roles['roles']:
                    await ctx.send(f'{ctx.author.mention}, That role has already been added')
                else:
                    self.roles['roles'].append(role.lower())
                    utils.save_cog_config(self, 'roles.json', self.roles)

                    full_role_name = giveable_roles[role.lower()].name
                    await ctx.send(f'Added: {full_role_name} as a givable role')

            else:
                await ctx.send((f"{ctx.author.mention}, "
                                "I cannot give that role to users as it is higher "
                                "than my highest role or it isn't a role in this guild"))

    @role.command()
    @commands.guild_only()
    @check_server()
    @permissions.check_admin()
    async def remove(self, ctx, *, role: str):
        '''
        Remove a role already set up on the guild from the list.
        So users can no longer use the bot to get the role
        '''

        if ctx.channel.id == BOT_CHANNEL_ID:
            # Get the roles the bot can give in the guild
            giveable_roles = self.get_givable_roles(ctx.guild)

            if role.lower() in self.roles['roles']:
                self.roles['roles'].remove(role.lower())
                utils.save_cog_config(self, 'roles.json', self.roles)

                full_role_name = giveable_roles[role.lower()].name
                await ctx.send(f'Removed: {full_role_name} as a givable role')

            else:
                await ctx.send(f"{ctx.author.mention}, That role isn't in the list")

    @role.command()
    @commands.guild_only()
    @check_server()
    async def join(self, ctx, *roles):
        '''
        Allows people to join the roles that have been set up.
        It will ignore roles not in the list
        '''

        if ctx.channel.id == BOT_CHANNEL_ID:
            # Get the roles the bot can give in the guild
            giveable_roles = self.get_givable_roles(ctx.guild)

            to_add = []
            for role_name in roles:
                if role_name.lower() in self.roles['roles']:
                    to_add.append(role_name)

            if to_add:
                added = []
                for role_name in to_add:
                    if giveable_roles[role_name.lower()] in ctx.author.roles:
                        continue
                    else:
                        await ctx.author.add_roles(giveable_roles[role_name.lower()])
                        added.append(giveable_roles[role_name.lower()].name)
                        await asyncio.sleep(1)

                if added:
                    await ctx.send("Roles added!: {0}".format(', '.join(added)))

                else:
                    await ctx.send("No vaild roles to be given or you already have them")

            else:
                await ctx.send("No vaild roles to be given")

    @role.command()
    @commands.guild_only()
    @check_server()
    async def leave(self, ctx, *roles):
        '''
        Allows people to leave the roles that have been set up.
        It will ignore roles they don't have
        '''

        if ctx.channel.id == BOT_CHANNEL_ID:
            # Get the roles the bot can give in the guild
            giveable_roles = self.get_givable_roles(ctx.guild)

            to_remove = []
            for role_name in roles:
                if role_name.lower() in self.roles['roles']:
                    to_remove.append(role_name)

            if to_remove:
                removed = []
                for role_name in to_remove:
                    if giveable_roles[role_name.lower()] not in ctx.author.roles:
                        continue
                    else:
                        await ctx.author.remove_roles(giveable_roles[role_name.lower()])
                        removed.append(giveable_roles[role_name.lower()].name)
                        await asyncio.sleep(1)

                if removed:
                    await ctx.send("Roles Removed!: {0}".format(', '.join(removed)))

                else:
                    await ctx.send("No vaild roles to be remove or you don't have any of them")

            else:
                await ctx.send("No vaild roles to be removed")

    @commands.command()
    async def report(self, ctx, user: discord.User, channel: discord.TextChannel, *, description: str):
        '''
        Reports a User to the staff.
        Use this function to report behaviour that does not adhere
        to the rules. Keep in mind that user names are case-sensitive
        and that you are able to pass ID's for both the user and the
        channel to be associated with the report. This is often useful
        when there are multiple users or channels with the same name
        that the bot can see (right click the channel -> Copy ID).
        '''

        guild: discord.Guild = self.bot.get_guild(GUILD_ID)

        if not all(u in guild.members for u in [ctx.author, user]):
            return await ctx.send(embed=discord.Embed(
                title="Failed to report User:",
                description=f"The reported User and you must be a member of the {guild.name} Guild.",
                colour=discord.Colour.red()
            ))
        elif channel not in guild.text_channels:
            return await ctx.send(embed=discord.Embed(
                title="Failed to report User:",
                description=f"The specified channel must be a text channel of the {guild.name} Guild.",
                colour=discord.Colour.red()
            ))

        report_channel = self.bot.get_channel(REPORT_CHANNEL_ID)
        await report_channel.send(embed=discord.Embed(
            title=f"New Report from {ctx.author.name} ({ctx.author.id})",
            colour=discord.Colour.orange()
        ).add_field(
            name="Reported User",
            value=f"**Name**: {user.name} (`{user.id}`)\n"
                  f"**Mention**: {user.mention}\n"
                  f"**In channel**: {channel.mention}"
        ).add_field(
            name="Report description",
            value=description,
            inline=False
        ))

    async def join_server(self, member):
        ''' Give user Guest role on join '''
        if member.guild.id == GUILD_ID:
            guest_role = discord.utils.get(member.guild.roles, name='Guest')
            await member.add_roles(guest_role)

    async def role_checker(self):
        '''
        Background check to make sure members don't have both
        Member and Guest roles if they do it removes Guest
        '''

        while True:
            guild = self.bot.get_guild(GUILD_ID)
            # Get both roles
            guest_role = discord.utils.get(guild.roles, name='Guest')
            member_role = discord.utils.get(guild.roles, name='Member')

            for member in guild.members:
                if member_role in member.roles and guest_role in member.roles:
                    await member.remove_roles(guest_role)

            await asyncio.sleep(300)

def setup(bot):
    ''' Add the cog to the bot '''
    cog = Programming(bot)
    bot.add_listener(cog.join_server, "on_member_join")
    bot.add_cog(cog)
