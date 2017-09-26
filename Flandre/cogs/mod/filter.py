'''
Holds the filter functions
'''
import logging

from .. import utils

logger = logging.getLogger(__package__)

async def make_filter_list(ctx, msg_filter, channel=False):
    '''
    Sends the user the filter words list for the channel or guild
    '''

    guild_id = str(ctx.guild.id)
    filtered_list = []

    if channel:
        channel_id = str(ctx.channel.id)
        if channel_id in msg_filter[guild_id]['channels']:
            msg = f'Channel Only Filter for {ctx.channel.name}:\n```\n'
            filtered_list = msg_filter[guild_id]['channels'][channel_id]
        else:
            await ctx.send(('Nothing is being filtered in this channel '
                            '(except server wide filter)'))
            return
    else:
        if msg_filter[guild_id]['server']:
            msg = f'Server Wide Filter for {ctx.guild.name}:\n```\n'
            filtered_list = msg_filter[guild_id]['server']
        else:
            await ctx.send('Nothing is being filtered server wide')
            return

    if filtered_list:
        for filtered in filtered_list:
            msg += '"{0}" '.format(filtered)
            # If the length of the messages is greater than 1600
            # Send it and make another message for the rest
            if len(msg) > 1600:
                msg += '\n```'
                await ctx.author.send(msg)
                msg = '```\n'
            # Send message
            msg += '\n```'
            await ctx.author.send(msg)
            await ctx.send('List sent in DM')

async def filter_add(ctx, msg_filter, words, channel=False):
    '''
    Adds the words to the filter for the channel or guild
    '''

    guild_id = str(ctx.guild.id)
    words_added = False

    if guild_id not in msg_filter:
        msg_filter[guild_id] = {'message': None, 'server': [], 'channels': {}}
        logger.info((f'Server {ctx.guild.name} ({ctx.guild.id}) '
                     'has been added to the filter'))

    if channel:
        channel_id = str(ctx.channel.id)
        if channel_id not in msg_filter[guild_id]['channels']:
            msg_filter[guild_id]['channels'][channel_id] = []

    # Loop over each word in words
    for word in words:
        word = word.lower()

        # Check if word is already being filtered if it is just ignore it
        if channel:
            if word in msg_filter[guild_id]['channels'][channel_id]:
                continue
            else:
                msg_filter[guild_id]['channels'][channel_id].append(word)
                words_added = True
        else:
            if word in msg_filter[guild_id]['server']:
                continue
            else:
                msg_filter[guild_id]['server'].append(word)
                words_added = True

    # Save the file if needed
    if words_added:
        logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                     'has added words to filter'))

        utils.save_cog_file('mod', 'filter.json', msg_filter)

    # Send message saying words have been added
    if channel:
        await ctx.send((f'{ctx.author.mention}, '
                        'Words have been added to the current channels filter'))
    else:
        await ctx.send((f'{ctx.author.mention}, '
                        'Words have been added to the server wide filter'))

    return msg_filter
    