''' Holds the util functions for the music cog '''
import os
import json
import logging

logger = logging.getLogger(__package__)

def load_channels_file():
    '''
    Loads channels.json from the data folder
    Will create the file and folder if it does not exist
    '''

    # Get the packages path
    package_path = os.path.dirname(__file__)

    # Check if there is a data folder in the package
    if not os.path.isdir(f'{package_path}\data'):
        logger.warning(f'`{package_path}\data` does not exist. It has been made for you')
        os.mkdir(f'{package_path}\data')

    # Try to load the file
    try:
        with open(f'{package_path}\data\channels.json', 'r') as file:
            return json.load(file)
    
    except Exception as err:
        # Log that the file could not be loaded
        logger.error(f'`{package_path}\data\channels.json` could not be loaded', exc_info=err)

        # Remake the file with the default info
        with open(f'{package_path}\data\channels.json', 'w') as file:
            json.dump({}, file, indent=4, sort_keys=True)
        
        logger.info(f'`{package_path}\data\channels.json` has been remade for you')

        return {}

def save_channels_file(data):
    '''
    Saves the data given in channels.json
    '''

    # Get the packages path
    package_path = os.path.dirname(__file__)

    # Try to save the file
    try:
        with open(f'{package_path}\data\channels.json', 'w') as file:
            json.dump(data, file, indent=4, sort_keys=True)

    except Exception as err:
        logger.critical(f'`{package_path}\data\channels.json` could not be saved. Please check it',
                        exc_info=err)
    else:
        logger.info(f'`{package_path}\data\channels.json` has been saved.')
