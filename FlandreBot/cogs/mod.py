import discord
from discord.ext import commands
from FlandreBot.utils.IO import files
import os
import logging
import json
import asyncio

class Mod:
    """Moderation tools."""

    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.loadConfig()
        self.ignore_list = files("FlandreBot/data/mod/ignorelist.json", "load")
        self.filter = files("FlandreBot/data/mod/filter.json", "load")
        self.past_names = files("FlandreBot/data/mod/past_names.json", "load")
        
    @commands.command(no_pm=True, pass_context=True)
    async def testserver(self, ctx):
        """get server id and channel id

        """
        
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkOwner(author):
            return
        
        message = ctx.message
        server = message.server
        channel = message.channel
        await self.bot.whisper("test")
        await self.bot.whisper("server id: " + server.id + " | channel id: " + channel.id)  
        await self.bot.delete_message(message)    

    @commands.command(no_pm=True, pass_context=True)
    async def kick(self, ctx, user : discord.Member):
        """Kicks user."""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkMod(author, channel):
            return
        try:
            await self.bot.kick(user)
            await self.bot.say("Done. That felt good.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.command(no_pm=True, pass_context=True)
    async def ban(self, ctx, user : discord.Member, days : int=0):
        """Bans user and deletes last X days worth of messages.

        Minimum 0 days, maximum 7. Defaults to 0."""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkAdmin(author, channel):
            return
        if days < 0 or days > 7:
            await self.bot.say("Invalid days. Must be between 0 and 7.")
            return
        try:
            await self.bot.ban(user, days)
            await self.bot.say("Done. It was about time.")
        except discord.errors.Forbidden:
            await self.bot.say("I'm not allowed to do that.")
        except Exception as e:
            print(e)

    @commands.command(no_pm=True, pass_context=True)
    async def rename(self, ctx, user : discord.Member, *, nickname=""):
        """Changes user's nickname

        Leaving the nickname empty will remove it."""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkMod(author, channel):
            return
        nickname = nickname.strip()
        if nickname == "":
            nickname = None
        try:
            await self.bot.change_nickname(user, nickname)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I cannot do that, I lack the "
                "\"Manage Nicknames\" permission.")

    @commands.group(pass_context=True, no_pm=True)
    async def cleanup(self, ctx):
        """Deletes messages.

        cleanup messages [number]
        cleanup user [name/mention] [number]
        cleanup text \"Text here\" [number]"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @cleanup.command(pass_context=True, no_pm=True)
    async def text(self, ctx, text : str, number : int):
        """Deletes last X messages matching the specified text.

        Example:
        cleanup text \"test\" 5

        Remember to use double quotes."""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkMod(author, channel):
            return
        message = ctx.message
        cmdmsg = message
        try:
            if number > 0 and number < 10000:
                while True:
                    new = False
                    async for x in self.bot.logs_from(message.channel, limit=100, before=message):
                        if number == 0: 
                            await self.bot.delete_message(cmdmsg)
                            await asyncio.sleep(0.25)
                            return
                        if text in x.content:
                            await self.bot.delete_message(x)
                            await asyncio.sleep(0.25)
                            number -= 1
                        new = True
                        message = x
                    if not new or number == 0: 
                        await self.bot.delete_message(cmdmsg)
                        await asyncio.sleep(0.25)
                        break
        except discord.errors.Forbidden:
            await self.bot.say("I need permissions to manage messages in this channel.")

    @cleanup.command(pass_context=True, no_pm=True)
    async def user(self, ctx, user : discord.Member, number : int):
        """Deletes last X messages from specified user.

        Examples:
        cleanup user @\u200bTwentysix 2
        cleanup user Red 6"""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkMod(author, channel):
            return
        message = ctx.message
        cmdmsg = message
        try:
            if number > 0 and number < 10000:
                while True:
                    new = False
                    async for x in self.bot.logs_from(message.channel, limit=100, before=message):
                        if number == 0: 
                            await self.bot.delete_message(cmdmsg)
                            await asyncio.sleep(0.25)
                            return
                        if x.author.id == user.id:
                            await self.bot.delete_message(x)
                            await asyncio.sleep(0.25)
                            number -= 1
                        new = True
                        message = x
                    if not new or number == 0: 
                        await self.bot.delete_message(cmdmsg)
                        await asyncio.sleep(0.25)
                        break
        except discord.errors.Forbidden:
            await self.bot.say("I need permissions to manage messages in this channel.")

    @cleanup.command(pass_context=True, no_pm=True)
    async def messages(self, ctx, number : int):
        """Deletes last X messages.

        Example:
        cleanup messages 26"""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkMod(author, channel):
            return
        channel = ctx.message.channel
        try:
            if number > 0 and number < 10000:
                async for x in self.bot.logs_from(channel, limit=number+1):
                    await self.bot.delete_message(x)
                    await asyncio.sleep(0.25)
        except discord.errors.Forbidden:
            await self.bot.say("I need permissions to manage messages in this channel.")

    @commands.group(pass_context=True, no_pm=True)
    async def ignore(self, ctx):
        """Adds servers/channels to ignorelist"""
        
        if ctx.invoked_subcommand is None:
            message = """"```examples:\n!ignore channel\n!ignore server"""
            await self.bot.say(message)
            await self.bot.say(self.count_ignored())

    @ignore.command(name="channel", pass_context=True)
    async def ignore_channel(self, ctx, channel : discord.Channel=None):
        """Ignores channel

        Defaults to current one"""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkAdmin(author, channel):
            return
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(current_ch.id)
                files("FlandreBot/data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")
        else:
            if channel.id not in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].append(channel.id)
                files("FlandreBot/data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("Channel added to ignore list.")
            else:
                await self.bot.say("Channel already in ignore list.")


    @ignore.command(name="server", pass_context=True)
    async def ignore_server(self, ctx):
        """Ignores current server"""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkAdmin(author, channel):
            return
        server = ctx.message.server
        if server.id not in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].append(server.id)
            files("FlandreBot/data/mod/ignorelist.json", "save", self.ignore_list)
            await self.bot.say("This server has been added to the ignore list.")
        else:
            await self.bot.say("This server is already being ignored.")

    @commands.group(pass_context=True, no_pm=True)
    async def unignore(self, ctx):
        """Removes servers/channels from ignorelist"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
            await self.bot.say(self.count_ignored())

    @unignore.command(name="channel", pass_context=True)
    async def unignore_channel(self, ctx, channel : discord.Channel=None):
        """Removes channel from ignore list

        Defaults to current one"""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkAdmin(author, channel):
            return
        current_ch = ctx.message.channel
        if not channel:
            if current_ch.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(current_ch.id)
                files("FlandreBot/data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("This channel has been removed from the ignore list.")
            else:
                await self.bot.say("This channel is not in the ignore list.")
        else:
            if channel.id in self.ignore_list["CHANNELS"]:
                self.ignore_list["CHANNELS"].remove(channel.id)
                files("FlandreBot/data/mod/ignorelist.json", "save", self.ignore_list)
                await self.bot.say("Channel removed from ignore list.")
            else:
                await self.bot.say("That channel is not in the ignore list.")


    @unignore.command(name="server", pass_context=True)
    async def unignore_server(self, ctx):
        """Removes current server from ignore list"""
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkAdmin(author, channel):
            return
        server = ctx.message.server
        if server.id in self.ignore_list["SERVERS"]:
            self.ignore_list["SERVERS"].remove(server.id)
            files("FlandreBot/data/mod/ignorelist.json", "save", self.ignore_list)
            await self.bot.say("This server has been removed from the ignore list.")
        else:
            await self.bot.say("This server is not in the ignore list.")

    def count_ignored(self):
        msg = "```Currently ignoring:\n"
        msg += str(len(self.ignore_list["CHANNELS"])) + " channels\n"
        msg += str(len(self.ignore_list["SERVERS"])) + " servers\n```\n"
        return msg

    @commands.group(name="filter", pass_context=True, no_pm=True)
    async def _filter(self, ctx):
        """Adds/removes words from filter

        Use double quotes to add/remove sentences
        Using this command with no subcommands will send
        the list of the server's filtered words."""
        
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkMod(author, channel):
            return
        
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
            server = ctx.message.server
            author = ctx.message.author
            msg = ""
            if server.id in self.filter.keys():
                if self.filter[server.id] != []:
                    word_list = self.filter[server.id]
                    for w in word_list:
                        msg += '"' + w + '" '
                    await self.bot.send_message(author, "Words filtered in this server: " + msg)

    @_filter.command(name="add", pass_context=True)
    async def filter_add(self, ctx, *words : str):
        """Adds words to the filter

        Use double quotes to add sentences
        Examples:
        filter add word1 word2 word3
        filter add \"This is a sentence\""""
        if words == ():
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
            return
        server = ctx.message.server
        added = 0
        if server.id not in self.filter.keys():
            self.filter[server.id] = []
        for w in words:
            if w.lower() not in self.filter[server.id] and w != "":
                self.filter[server.id].append(w.lower())
                added += 1
        if added:
            files("FlandreBot/data/mod/filter.json", "save", self.filter)
            await self.bot.say("Words added to filter.")
        else:
            await self.bot.say("Words already in the filter.")

    @_filter.command(name="remove", pass_context=True)
    async def filter_remove(self, ctx, *words : str):
        """Remove words from the filter

        Use double quotes to remove sentences
        Examples:
        filter remove word1 word2 word3
        filter remove \"This is a sentence\""""
        if words == ():
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
            return
        server = ctx.message.server
        removed = 0
        if server.id not in self.filter.keys():
            await self.bot.say("There are no filtered words in this server.")
            return
        for w in words:
            if w.lower() in self.filter[server.id]:
                self.filter[server.id].remove(w.lower())
                removed += 1
        if removed:
            files("FlandreBot/data/mod/filter.json", "save", self.filter)
            await self.bot.say("Words removed from filter.")
        else:
            await self.bot.say("Those words weren't in the filter.")

    @commands.group(no_pm=True, pass_context=True)
    async def editrole(self, ctx):
        """Edits roles settings"""
        
        author = ctx.message.author
        channel = ctx.message.channel
        if not self.checkAdmin(author, channel):
            return
        
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @editrole.command(aliases=["color"], pass_context=True)
    async def colour(self, ctx, role : discord.Role, value : discord.Colour):
        """Edits a role's colour

        Use double quotes if the role contains spaces.
        Colour must be in hexadecimal format.
        \"http://www.w3schools.com/colors/colors_picker.asp\"
        #cefdf9 -> 0xcefdf9
        Examples:
        !editrole colour \"The Transistor\" 0xffff00
        !editrole colour Test 0xcefdf9"""
        author = ctx.message.author
        try:
            await self.bot.edit_role(ctx.message.server, role, color=value)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I need permissions to manage roles first.")
        except Exception as e:
            print(e)
            await self.bot.say("Something went wrong.")

    @editrole.command(name="name", pass_context=True)
    async def edit_role_name(self, ctx, role : discord.Role, name : str):
        """Edits a role's name

        Use double quotes if the role or the name contain spaces.
        Examples:
        !editrole name \"The Transistor\" Test"""
        if name == "":
            await self.bot.say("Name cannot be empty.")
            return
        try:
            author = ctx.message.author
            old_name = role.name # probably not necessary?
            await self.bot.edit_role(ctx.message.server, role, name=name)
            await self.bot.say("Done.")
        except discord.Forbidden:
            await self.bot.say("I need permissions to manage roles first.")
        except Exception as e:
            print(e)
            await self.bot.say("Something went wrong.")

    @commands.command(pass_context = True, no_pm = True)
    async def info(self, ctx):
        ''' Get users Stats '''
        message = ctx.message

        if len(message.mentions) == 0:
            user = message.author
        else:
            user = message.mentions[0]

        # Get users last sent message
        messages = self.bot.messages
        messages.reverse()
        last_message = discord.utils.get(messages, author__id=user.id)
        del messages

        # Get users top role
        if user.top_role.name == '@everyone':
            role = user.top_role.name[1:]
        else:
            role = user.top_role.name

        embedcolour = discord.Colour(65535)
        userembed = discord.Embed(type='rich', colour=embedcolour)
        userembed.add_field(name='Name', value=user.name)
        userembed.add_field(name='ID', value=user.id)

        # Check for nickname
        if user.nick is not None:
            userembed.add_field(name='Nickname', value=user.nick)

        userembed.add_field(name='Created', value=user.created_at)
        userembed.add_field(name='Joined', value=user.joined_at)

        # Check voice channel
        if user.voice.voice_channel is not None:
            userembed.add_field(name='Voice Channel', value=user.voice.voice_channel.name)

        # Get Users roles
        roles = [role.name for role in user.roles if role.name != '@everyone']
        if roles:
            userembed.add_field(name='Roles', value=', '.join(roles), inline=False)

        # get past names
        if user.id in self.past_names:
            names = ', '.join(self.past_names[user.id][-5:])
            userembed.add_field(name='Past names', value=names, inline=False)
        
        # Check for last message
        if last_message is not None:
            userembed.add_field(name='Last Message', value=last_message.content, inline=False)

        # Set users avatar
        userembed.set_thumbnail(url=user.avatar_url)

        await self.bot.say(embed=userembed)        
            
    @commands.command()
    async def names(self, user : discord.Member):
        """Show previous names of a user"""
        exclude = ("@everyone", "@here")
        if user.id in self.past_names.keys():
            names = ""
            for name in self.past_names[user.id]:
                if not any(mnt in name.lower() for mnt in exclude):
                    names += " {}".format(name)
            names = "```{}```".format(names)
            await self.bot.say("Past names:\n{}".format(names))
        else:
            await self.bot.say("That user doesn't have any recorded name change.")

    async def check_filter(self, message):
        if message.channel.is_private:
            return
        server = message.server
        channel = message.channel
        can_delete = message.channel.permissions_for(server.me).manage_messages

        if message.author.id == self.bot.user.id or self.immune_from_filter(message) or not can_delete: # Owner, admins and mods are immune to the filter
            return
            
        if server.id == "181866934353133570":   
            if channel.id == "209074609893408768":
                if message.content.lower() == "!agree":
                    try: # Something else in discord.py is throwing a 404 error after deletion
                        await self.bot.delete_message(message)
                        author = message.author
                        guest = discord.utils.get(message.server.roles, name="Guest")
                        member = discord.utils.get(message.server.roles, name="Member")
                        if guest in message.author.roles:
                            try:
                                await self.bot.remove_roles(author, guest)
                            except:
                                pass
                            
                    except:
                        pass
                else:
                    try: # Something else in discord.py is throwing a 404 error after deletion
                        await self.bot.delete_message(message)
                    except:
                        pass
        elif server.id in self.filter.keys():
            for w in self.filter[server.id]:
                if w in message.content.lower():
                    try: # Something else in discord.py is throwing a 404 error after deletion
                        await self.bot.delete_message(message)
                    except:
                        pass
                    print("Message deleted. Filtered: " + w )
					
    
    async def check_names(self, before, after):
        if before.name != after.name:
            if before.id not in self.past_names.keys():
                self.past_names[before.id] = [before.name]
            else:
                if before.name not in self.past_names[before.id]:
                    self.past_names[before.id].append(before.name)
            files("FlandreBot/data/mod/past_names.json", "save", self.past_names)
            
            
    def checkAdmin(self, user, channel):
        return (user.permissions_in(channel).manage_server)
        
    def checkMod(self, user, channel):
        return (user.permissions_in(channel).manage_channels)
        
    def checkOwner(self, user):
        return (user.id == self.config['ownerid'])
        
    def immune_from_filter(self, message):
        user = message.author
        server = message.server
        channel = message.channel

        if self.checkOwner(user):
            return True
        elif self.checkMod(user, channel):
            return True
        elif self.checkAdmin(user, channel):
            return True
        else:
            return False
        
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
    if not os.path.exists("FlandreBot/data/mod"):
        print("Creating FlandreBot/data/mod folder...")
        os.makedirs("FlandreBot/data/mod")

def check_files():
    ignore_list = {"SERVERS" : [], "CHANNELS" : []}

    if not os.path.isfile("FlandreBot/data/mod/blacklist.json"):
        print("Creating empty blacklist.json...")
        files("FlandreBot/data/mod/blacklist.json", "save", [])

    if not os.path.isfile("FlandreBot/data/mod/whitelist.json"):
        print("Creating empty whitelist.json...")
        files("FlandreBot/data/mod/whitelist.json", "save", [])

    if not os.path.isfile("FlandreBot/data/mod/ignorelist.json"):
        print("Creating empty ignorelist.json...")
        files("FlandreBot/data/mod/ignorelist.json", "save", ignore_list)

    if not os.path.isfile("FlandreBot/data/mod/filter.json"):
        print("Creating empty filter.json...")
        files("FlandreBot/data/mod/filter.json", "save", {})

    if not os.path.isfile("FlandreBot/data/mod/past_names.json"):
        print("Creating empty past_names.json...")
        files("FlandreBot/data/mod/past_names.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = Mod(bot)
    bot.add_listener(n.check_filter, "on_message")
    bot.add_listener(n.check_names, "on_member_update")
    bot.add_cog(n)
