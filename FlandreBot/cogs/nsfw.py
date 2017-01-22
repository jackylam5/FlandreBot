from discord.ext import commands
import io
import aiohttp
import xmltodict
import random
import re
import json
from discord import Embed, Colour, utils
from bs4 import BeautifulSoup
import io

botchannelname = {"bot"}

class nsfw:
    """NSFW commands."""

    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.loadConfig()


    @commands.command(no_pm=True, pass_context=True)
    async def nsfw(self, ctx):
        """get nsfw role
        """

        if self.botCheck(ctx):
            try:
                testrole = utils.get(ctx.message.server.roles, name="nsfw")
                author = ctx.message.author
                if testrole not in author.roles:
                    await self.bot.add_roles(author, testrole)
                    await self.bot.say("nsfw role added")
                else:
                    await self.bot.remove_roles(author, testrole)
                    await self.bot.say("nsfw role removed")
            except:
                await self.bot.say("Something went wrong.")        
        else:
            await self.bot.say("bot room only command")


            
    @commands.command(pass_context=True)
    async def gelbooru(self, ctx, *tags):
        """Search pictures on gelbooru.
        """
        

        message = ctx.message
        author = message.author
        
        
        if not self.nsfwCheck(ctx):
            await self.bot.say('{} please use nsfw channels for this'.format(author.mention))
            return
        
        linktags = ""
        
        if len(tags) > 0:

            for p in tags:
                replaced = re.sub(' ', '_', str(p))
                linktags = linktags + "+" + str(replaced)
            

        
        
        base_url = 'http://gelbooru.com/index.php?page=dapi&s=post&q=index&limit={0}&pid={1}&tags={2}'
        post_url = 'http://gelbooru.com/index.php?page=post&s=view&id={0}'
        
        #check for images
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(base_url.format(0, 0, linktags)) as resp:
                status_code = resp.status
                data = await resp.text()
                
        if status_code == 200:
            info = xmltodict.parse(data)
            if int(info['posts']['@count']) != 0:
                # Get the number of pages and randomly pick one
                num_pages = int(int(info['posts']['@count']) / 100)
                page = random.randint(0, num_pages)

                # Download the info about images with 100 images and page set
                with aiohttp.ClientSession() as aioclient:
                    async with aioclient.get(base_url.format(100, page, linktags)) as resp:
                        data = await resp.text()
                info = xmltodict.parse(data)

                # Choose Image
                if int(info['posts']['@count']) == 1:
                    image = info['posts']['post']
                else:
                    image = random.choice(info['posts']['post'])
                try:
                    colour = Colour(15839969)
                    embed = Embed(type='rich', colour=colour)
                    embed.set_image(url=image['@file_url'])
                    embed.set_author(name='Gelbooru', url=post_url.format(image['@id']))
                    await self.bot.send_message(message.channel, embed=embed)
                except KeyError:
                    await self.bot.send_message(message.channel, '{0.mention}, Sorry I couldn\'t get the url for the image I found'.format(message.author))
            else:
                await self.bot.send_message(message.channel, '{0.mention}, Nothing found with the tag(s) supplied.'.format(message.author))
        else:
            await self.bot.send_message(message.channel, '{0.mention}, Gelbooru seems to be down right now (Status Code: {1}).'.format(message.author, str(status_code)))
    
    @commands.command(pass_context=True)
    async def danbooru(self, ctx, *tags):
        """Search pictures on danbooru.
        """
        

        message = ctx.message
        author = message.author
        
        
        if not self.nsfwCheck(ctx):
            await self.bot.say('{} please use nsfw channels for this'.format(author.mention))
            return
        
        linktags = ""
        
        if len(tags) > 0:

            for p in tags:
                replaced = re.sub(' ', '_', str(p))
                linktags = linktags + "+" + str(replaced)
            
        
        base_url = 'http://danbooru.donmai.us/posts.json?limit=1&random=true&tags={0}'
        post_url = 'http://danbooru.donmai.us/posts/{0}'
        
        #check for images
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(base_url.format(linktags)) as resp:
                data = await resp.json()
                
        if len(data) != 0:
            try:
                colour = Colour(15839969)
                embed = Embed(type='rich', colour=colour)
                embed.set_image(url='http://danbooru.donmai.us' + data[0]['file_url'])
                embed.set_author(name='Danbooru', url=post_url.format(data[0]['id']))
                await self.bot.send_message(message.channel, embed=embed)
            except KeyError:
                    await self.bot.send_message(message.channel, '{0.mention}, Sorry I couldn\'t get the url for the image I found'.format(message.author))
        else:
            await self.bot.send_message(message.channel, '{0.mention}, Nothing found with the tag(s) supplied.'.format(message.author))
    
    @commands.command(pass_context=True)
    async def kona(self, ctx, *tags):
        """Search pictures on konachan.
        """
        

        message = ctx.message
        author = message.author
        
        
        if not self.nsfwCheck(ctx):
            await self.bot.say('{} please use nsfw channels for this'.format(author.mention))
            return
        
        linktags = "order:random"
        
        if len(tags) > 0:

            for p in tags:
                replaced = re.sub(' ', '_', str(p))
                linktags = linktags + "+" + str(replaced)
            
        
        base_url = 'http://konachan.com/post.json?limit={0}&page={1}&tags={2}'
        post_url = 'http://konachan.com/post/show/{0}'
        
        #check for images
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(base_url.format(1, 1, linktags)) as resp:
                data = await resp.json()
                
        if len(data) != 0:
            try:
                colour = Colour(15839969)
                embed = Embed(type='rich', colour=colour)
                embed.set_image(url="https://" + data[0]['file_url'][2:])
                embed.set_author(name='Konachan', url=post_url.format(data[0]['id']))
                await self.bot.send_message(message.channel, embed=embed)
            except KeyError:
                    await self.bot.send_message(message.channel, '{0.mention}, Sorry I couldn\'t get the url for the image I found'.format(message.author))
        else:
            await self.bot.send_message(message.channel, '{0.mention}, Nothing found with the tag(s) supplied.'.format(message.author))
    
    @commands.command(pass_context=True)
    async def yandere(self, ctx, *tags):
        """Search pictures on yandere.
        """
        

        message = ctx.message
        author = message.author
        
        
        if not self.nsfwCheck(ctx):
            await self.bot.say('{} please use nsfw channels for this'.format(author.mention))
            return
        
        linktags = "order:random"
        
        if len(tags) > 0:
            
            for p in tags:
                replaced = re.sub(' ', '_', str(p))
                linktags = linktags + "+" + str(replaced)
            
        base_url = 'https://yande.re/post.json?limit=1&tags={0}&login={1}&password_hash={2}'
        post_url = 'https://yande.re/post/show/{0}'
        
        loginname = self.config['yanderelogin']
        loginpw = self.config['yanderepw']
        
        #check for images
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(base_url.format(linktags, loginname, loginpw)) as resp:
                data = await resp.json()
                
        if len(data) != 0:
            try:
                colour = Colour(15839969)
                embed = Embed(type='rich', colour=colour)
                embed.set_image(url=data[0]['file_url'])
                embed.set_author(name='Yandere', url=post_url.format(data[0]['id']))
                await self.bot.send_message(message.channel, embed=embed)
            except KeyError:
                    await self.bot.send_message(message.channel, '{0.mention}, Sorry I couldn\'t get the url for the image I found'.format(message.author))
        else:
            await self.bot.send_message(message.channel, '{0.mention}, Nothing found with the tag(s) supplied.'.format(message.author))
    
    @commands.command(pass_context=True)
    async def sankaku(self, ctx, *tags):
        ''' Search pictures on sankaku complex
        This command might take a while to get an image
        It is also not formatted nicely due to image not going in embed
        '''

        message = ctx.message
        base_url = 'https://chan.sankakucomplex.com/?tags={0}'

        if not self.nsfwCheck(ctx):
            await self.bot.say('{} please use nsfw channels for this'.format(message.author.mention))
            return

        linktags = "order:random"
        
        if len(tags) > 0:
            
            for p in tags:
                replaced = re.sub(' ', '_', str(p))
                linktags = linktags + "+" + str(replaced)

        # Get webpage to pick image
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(base_url.format(linktags), headers={'User-Agent': 'Googlebot-Image/1.0'}) as resp:
                data = await resp.text()

        # Open webpage with bs4
        soup = BeautifulSoup(data, 'html.parser')
        images = soup.find_all('img', {'class': 'preview'})
        if len(images) != 0:
            image = random.choice(images)
            post_url = 'https://chan.sankakucomplex.com' + image.parent['href']        
             # Get image
            with aiohttp.ClientSession() as aioclient:
                async with aioclient.get(post_url, headers={'User-Agent': 'Googlebot-Image/1.0'}) as resp:
                    data = await resp.text()

            soup = BeautifulSoup(data, 'html.parser')
            bigimage = soup.find_all('img', {'id': 'image'})
            image_url = 'https:' + bigimage[0]['src']

            try:
                # Get webpage to pick image
                with aiohttp.ClientSession() as aioclient:
                    async with aioclient.get(image_url, headers={'User-Agent': 'Googlebot-Image/1.0'}) as resp:
                        data = await resp.read()

                image_io = io.BytesIO(data)
                image_io.seek(0)
                ext = bigimage[0]['src'].split('.')[-1].split('?')[0]

                await self.bot.send_file(message.channel, fp=image_io, filename='sankaku.{0}'.format(ext))
                image_io.close()
                del image_io
            except KeyError:
                await self.bot.send_message(message.channel, '{0.mention}, Sorry I couldn\'t get the url for the image I found'.format(message.author))
        else:
            await self.bot.send_message(message.channel, '{0.mention}, Nothing found with the tag(s) supplied.'.format(message.author))


    def loadConfig(self):
        ''' Load the config from the config.json file '''
        try:
            with open('FlandreBot/config.json', 'r') as config:
                self.config = json.load(config)
        except json.decoder.JSONDecodeError:
            pass
        
    def nsfwCheck(self, ctx):
        user = ctx.message.author
        channel = ctx.message.channel
        if channel.is_private or 'nsfw' in channel.name.lower():
            return True
        return False
        
    def botCheck(self, ctx):
        channel = ctx.message.channel
        if 'bot' in channel.name.lower() and not channel.is_private:
            return True
        return False




def setup(bot):
    n = nsfw(bot)
    bot.add_cog(n)
