import discord
from discord.ext import commands
import importlib
from Flandre import permissions

class Owner:
    ''' These commands are for bot owners only
    It allows you to reload/load/unload cogs 
    '''
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def reload(self, ctx, *, module: str):
        '''Reload modules.'''
        
        # Get the message sent
        message = ctx.message

        # Log that the cog is being reloaded and by who
        self.bot.logger.info("Reload module: {0}. Requested by {1.name}#{1.discriminator}".format(module, message.author))
        
        try:
            # Get the module's cog and check it has a _unload function in it (Must be an async function)
            cog = self.bot.get_cog(module)
            unload_function = getattr(cog, "_unload", None)
            if unload_function is not None:
                self.bot.logger.info("Cog has a _unload function. Running it")
                await unload_function()

            self.reloadcog(module)
            self.bot.logger.info("Reloaded: {}".format(module))
            await self.bot.say("Done reloading: {}".format(module))
        except Exception as e:
            self.bot.logger.critical("Reload failed. Reason: {}".format(e))
            await self.bot.say("Something went wrong. Check log to see what it was")

            
    @commands.command(pass_context=True)
    @permissions.checkOwner()
    async def load(self, ctx, *, module: str):
        '''Load modules.'''
        
        # Get the message sent
        message = ctx.message

        # Log that the cog is being loaded and by who
        self.bot.logger.info("Load module: {0}. Requested by {1.name}#{1.discriminator}".format(module, message.author))
        
        try:
            self.loadcog(module)
            self.bot.logger.info("Loaded: {}".format(module))
            await self.bot.say("Done loading: {}".format(module))

        except Exception as e:
            self.bot.logger.critical("Load failed. Reason: {}".format(e))
            await self.bot.say("Something went wrong. Check log to see what it was")
    
    @commands.command(pass_context=True)    
    @permissions.checkOwner()
    async def unload(self, ctx, *, module: str):
        '''Unload modules.'''
        
        # Get the message sent
        message = ctx.message

        # Log that the cog is being unloaded and by who
        self.bot.logger.info("Unload module: {0}. Requested by {1.name}#{1.discriminator}".format(module, message.author))

        try:
            # Get the module's cog and check it has a _unload function in it (Must be an async function)
            cog = self.bot.get_cog(module)
            unload_function = getattr(cog, "_unload", None)
            if unload_function is not None:
                self.bot.logger.info("Cog has a _unload function. Running it")
                await unload_function()

            self.unloadcog(module)
            self.bot.logger.info("Unloaded: {}".format(module))
            await self.bot.say("Done unloading: {}".format(module))

        except Exception as e:
            self.bot.logger.critical("Unload failed. Reason: {}".format(e))
            await self.bot.say("Something went wrong. Check log to see what it was")
    
    #reload function
    def reloadcog(self, cog):
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.unload_extension(cog)
        self.bot.load_extension(cog)
        
    def loadcog(self, cog):
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.load_extension(cog)
      
    def unloadcog(self, cog):
        if not "Flandre.cogs." in cog:
            cog = "Flandre.cogs." + cog
        self.bot.unload_extension(cog)                     
                

def setup(bot):
    bot.add_cog(Owner(bot))