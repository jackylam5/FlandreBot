''' error.py
Written by jackylam5 & maware
Holds all the custom errors
'''

class MissingConfigFile(Exception):
    ''' The error raised if the config file is missing '''
    pass

class LoginError(Exception):
    ''' The error raised if token is missing from config '''
    pass
