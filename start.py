''' start.py
Written by Scrubs (jackylam5 & maware)
Starts the bot
If errors occurs the script will terminate
Or try to restart the bot after 20 seconds
'''

import Flandre
import asyncio
import logging
from discord import LoginFailure, ClientException, DiscordException
from time import sleep

# Set up a log for when the bot restarts incase user is away and the bot completely dies
logger = logging.getLogger('Flandre-start.py')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(filename='Flandre-StartErrors.log', encoding='utf-8', mode='w')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s > %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Run the bot and set up auto-restart
run = True
while run:
    try:
        loop = asyncio.get_event_loop()
        bot = Flandre.Bot()
        # Start bot
        loop.run_until_complete(bot.start())
    except Flandre.MissingConfigFile as e:
        # Missing Config File
        logger.critical("Config File Missing: {}".format(e))
        logger.info("A config file has been made for you (Flandre/config.json). Please fill it out and restart the bot")
        run = False
    except LoginFailure as e:
        # LogIn Fails
        loop.run_until_complete(bot.logout())
        logger.critical("Login Failed: {}".format(e))
        run = False
    except (ClientException, DiscordException):
        # Discord disconnected the bot
        loop.run_until_complete(bot.logout())
        logger.error("Disconnected will try to reconnect: {}".format(e))
        run = True
        sleep(20)
    except Exception as e:
        # Any Unknown Exception
        logger.critical("Unknown Exception: {}".format(e))
        run = False
    finally:
        if run == False:
            loop.close()
