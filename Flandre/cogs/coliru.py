import aiohttp
import discord
from discord.ext import commands

class Coliru:
    """Evaluation Command(s) using the Coliru API."""
    def __init__(self, bot):
         self.bot = bot
 
    def __unload(self):
        pass

    @commands.command(name='eval')
    @commands.cooldown(rate=1, per=60., type=commands.BucketType.user)
    async def eval_(self, ctx):
        """Evaluate the given Codeblock. The language must be specified in the highlighter."""

        data = {"cmd": "g++ main.cpp && ./a.out", "src": "#include <iostream>\nint main(){    std::cout << \"Hello World!\" << std::endl;}"}
        async with aiohttp.ClientSession() as cs:
            async with cs.post('http://coliru.stacked-crooked.com/compile', data=data) as r:
                print(r.status)
                resp = await r.text()
                print(resp)
                print(r)
        
        await ctx.send(embed=discord.Embed(
                title='Eval Results'
            ).add_field(
                name='Output',
                value=f'```{resp}```'
             ))

def setup(bot):
    bot.add_cog(Coliru(bot))