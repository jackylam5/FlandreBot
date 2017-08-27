''' Util functions for the cog '''
import re

def clean_reason(bot, reason):
    ''' Removes ` from the reason to stop escaping and format mentions if in reason '''

    reason = reason.replace('`', '')

    matches = re.findall('(<@!?(\d*)>)', reason)

    for match in matches:
        user = bot.get_user(int(match[1]))
        reason = reason.replace(match[0], f'@{user.name}#{user.discriminator}')

    return reason
