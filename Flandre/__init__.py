import logging
from logging.handlers import RotatingFileHandler

from .core import Bot
from .errors import MissingConfigFile, LoginError

# Make the logger for the bot
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Make file handler for log file
file_handler = RotatingFileHandler(filename=f'{__package__}.log',
                                   maxBytes=5*1024*1024,
                                   backupCount=5)

file_handler.setLevel(logging.DEBUG)

# Make the format for log file
fmt_msg = '%(asctime)s - %(name)s - %(levelname)s > [%(funcName)s] %(message)s'
formatter = logging.Formatter(fmt_msg)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
