''' Holds the snipe cog '''

from discord.ext import commands
from .. import permissions, utils
import re
import requests
from bs4 import BeautifulSoup
import aiohttp
from time import time
from pixivpy3 import AppPixivAPI

config_default = {
    "channels": {}
}

image_types = ['.jpg', '.jpeg', '.png']
image_formats = ("image/png", "image/jpeg", "image/jpg")

# todo:
# - add ugoira support
# - add pixiv repost


class Mention(commands.Cog):
    ''' Auto mention
    '''

    def __init__(self, bot):
        self.bot = bot
        self.config = utils.check_cog_config(self, 'config.json', default=config_default)
        self.session = aiohttp.ClientSession()
        self.time = time()
        self.short_counter = 1
        self.long_counter = 1

    # help message
    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages

    @commands.group(name="mention", no_pm=True, pass_context=True)
    async def _mention(self, ctx):
        """ mention commands
        """

        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)

    @_mention.command(name='logchannel', no_pm=True, pass_context=True)
    @permissions.check_admin()
    async def _logchannel(self, ctx):
        """ Enable/Disable check in this channel for new images.
        """

        channel_id = str(ctx.message.channel.id)
        if "channels" not in self.config:
            self.config["channels"] = {"last_tag": [], "tags": {}}
            msg = "This channel will be used to check for new images."

        if channel_id in self.config["channels"]:
            self.config["channels"].pop(channel_id)
            msg = "This channel will no longer be used to check for new images."
            await ctx.send(msg)

        else:
            self.config["channels"][channel_id] = {"last_tag": [], "tags": {}}
            msg = "This channel will be used to check for new images."
            await ctx.send(msg)

        utils.save_cog_config(self, "config.json", self.config)

    @_mention.command(name='tag', no_pm=True, pass_context=True)
    async def _tag(self, ctx, tag=None):
        """ Adds the tag to the mention list.
        """

        channel_id = str(ctx.message.channel.id)

        if channel_id in self.config["channels"]:

            if tag is None:
                msg = "Please add a tag."
                await ctx.send(msg)
                return

            tag = tag.lower()

            user = ctx.message.author.id

            if tag not in self.config["channels"][channel_id]["tags"]:
                self.config["channels"][channel_id]["tags"][tag] = []

            config_tag = self.config["channels"][channel_id]["tags"][tag]

            if user in config_tag:
                msg = f"You already added the tag: {tag}."
                await ctx.send(msg)
            else:
                config_tag.append(user)
                msg = f"You will now get a mention if an image has the tag: {tag}."
                await ctx.send(msg)
                utils.save_cog_config(self, "config.json", self.config)

        else:
            msg = "Channel is not being logged for image check."
            await ctx.send(msg)

        utils.save_cog_config(self, "config.json", self.config)

    @_mention.command(name='untag', no_pm=True, pass_context=True)
    async def _untag(self, ctx, tag=None):
        """ Removes the tag to the mention list.
        """

        channel_id = str(ctx.message.channel.id)

        if channel_id in self.config["channels"]:

            if tag is None:
                msg = "Please add a tag."
                await ctx.send(msg)
                return

            tag = tag.lower()

            user = ctx.message.author.id

            if tag not in self.config["channels"][channel_id]["tags"]:
                return

            config_tag = self.config["channels"][channel_id]["tags"][tag]

            if user in config_tag:
                msg = f'You will no longer get mentioned for: {tag}.'
                config_tag.remove(user)
                utils.save_cog_config(self, "config.json", self.config)
                await ctx.send(msg)
            else:
                msg = f"Tag not found in user list."
                await ctx.send(msg)

        else:
            msg = "Channel is not being logged for image check."
            await ctx.send(msg)

        utils.save_cog_config(self, "config.json", self.config)

    @_mention.command(name='show', no_pm=True, pass_context=True)
    async def _show(self, ctx):
        """ Shows all tags in your mention list.
        """

        channel_id = str(ctx.message.channel.id)

        if channel_id in self.config["channels"]:

            tags = []
            user = ctx.message.author.id

            for item in self.config["channels"][channel_id]["tags"]:
                get_item = self.config["channels"][channel_id]["tags"][item]
                if len(get_item) > 0:
                    if user in get_item:
                        tags.append(item)
            msg = f'You will get mentioned in this channel for the following tags: \n{tags}'
            await ctx.message.author.send(msg)
            await ctx.send(f'<@{user}> check your DM!')

        else:
            msg = "Channel is not being logged for image check."
            await ctx.send(msg)

    @_mention.command(name='last', no_pm=True, pass_context=True)
    async def _last(self, ctx):
        """ Shows the tags of last image
        """

        channel_id = str(ctx.message.channel.id)

        if channel_id in self.config["channels"]:

            tags = []
            user = ctx.message.author.id

            tags = self.config["channels"][channel_id]["last_tag"]

            msg = f'The last image in channel has the following tags: \n{tags}'
            await ctx.message.author.send(msg)
            await ctx.send(f'<@{user}> check your DM!')

        else:
            msg = "Channel is not being logged for image check."
            await ctx.send(msg)

    async def get_message_info(self, message):
        """ Get information about the beatmap
        """

        # Check if the channel should be checked
        channel_id = str(message.channel.id)
        if "channels" not in self.config:
            self.config["channels"] = []

        if channel_id in self.config["channels"]:

            # check for all urls in message
            urls = re.findall(r'https?:\/\/.+?(?=[\s]|$)', message.content, flags=re.MULTILINE)

            # check for attachments
            if len(message.attachments) > 0:
                for attachment in message.attachments:
                    urls.append(attachment.url)

            for url in urls:

                # get image from the twitter link
                if 'twitter' in url:
                    async with self.session.get(url) as resp:
                        data = await resp.text()
                        soup = BeautifulSoup(data, 'html.parser')
                        urls = re.findall(r'https://pbs\.twimg\.com/media?.+?(?=[\s]|$)', str(soup), flags=re.MULTILINE)
                        url = urls[0][:-1]

                # check if the link is an image and reverse search
                r = requests.head(url)
                if r.headers["content-type"] in image_formats:

                    sources_found = 0
                    all_tags = []
                    mentions = []
                    ids = []
                    confidence = 0

                    search = f'http://iqdb.org/index.xml?url={url}'
                    async with self.session.get(search) as resp:
                        data = await resp.text()
                        soup = BeautifulSoup(data, 'html.parser')

                        matches = soup.find_all('match')

                        if not matches:
                            return

                        print(matches)

                        for match in matches:
                            if match is None:
                                continue

                            sim = None
                            tags = None

                            try:
                                sim = float(match['sim'])
                            except:
                                pass

                            try:
                                tags = match.post['tags']
                            except:
                                pass

                            try:
                                tags = match.post["theme_tags"]
                            except:
                                pass

                            if sim is None or tags is None:
                                continue

                            if sim > 80:

                                if sim > confidence:
                                    confidence = sim

                                sources_found += 1

                                tags = tags.lower().replace('"', '')
                                for tag in tags.split(" "):
                                    if tag not in all_tags:
                                        all_tags.append(tag)

                    resp.close()

                    # pixiv lookup
                    # check if the link is an image and reverse search

                    if self.long_counter > 0:
                        if time() - self.time > 30 or self.short_counter > 0:
                            session = aiohttp.ClientSession()
                            search = f'https://saucenao.com/search.php?db=5&api_key={self.bot.config["saucenao_api_key"]}&output_type=2&url={url}'
                            async with session.get(search) as resp:
                                data = await resp.json()
                                results_found = data["header"]["results_returned"]
                                short_remaining = data["header"]["short_remaining"]
                                long_remaining = data["header"]["long_remaining"]

                                self.short_counter = short_remaining
                                self.long_counter = long_remaining
                                if time() - self.time > 30:
                                    self.time = time()

                                if results_found > 0:
                                    all_results = data["results"]

                                    for result in all_results:
                                        sim = float(result["header"]["similarity"])
                                        if sim > 80:

                                            if sim > confidence:
                                                confidence = sim

                                            pixiv_id = result["data"]["pixiv_id"]
                                            api = AppPixivAPI()
                                            api.login(username=self.bot.config['pixiv_id'],
                                                      password=self.bot.config['pixiv_password'])
                                            api.set_accept_language('en-us')
                                            json_result = api.illust_detail(pixiv_id)
                                            illust = json_result.illust
                                            if illust.page_count == 1:
                                                pixiv_tags = illust.tags

                                                if len(pixiv_tags) > 0:
                                                    print(pixiv_tags)
                                                    for tag in pixiv_tags:
                                                        try:
                                                            if tag["name"] not in all_tags:
                                                                all_tags.append(tag["name"])
                                                            if tag["translated_name"] not in tags:
                                                                all_tags.append(tag["translated_name"].lower())
                                                            sources_found += 1
                                                        except:
                                                            pass

                            resp.close()

                    # add people to mention
                    for tag in self.config["channels"][channel_id]["tags"]:
                        tag = tag.lower()
                        if tag in all_tags:
                            for mention_id in self.config["channels"][channel_id]["tags"][tag]:
                                if mention_id not in ids:
                                    mentions.append(f'<@{mention_id}> ')
                                    ids.append(mention_id)

                    if mentions and sources_found:
                        self.config["channels"][channel_id]["last_tag"] = all_tags
                        utils.save_cog_config(self, "config.json", self.config)
                        send_message = f'Confidence: {confidence}%\n'
                        await message.channel.send(send_message + ' '.join(mentions))

    async def check_image(self, message):
        ''' Check if beatmap was sent '''
        if message.author != self.bot.user and not message.author.bot:
            await self.get_message_info(message)


def setup(bot):
    ''' Setup function to add cog to bot '''
    cog = Mention(bot)
    bot.add_listener(cog.check_image, "on_message")
    bot.add_cog(cog)
