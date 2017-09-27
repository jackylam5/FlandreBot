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
    else:
        await ctx.send(f'{ctx.author.mention}, Nothing has been added to the filter')

    return msg_filter

async def filter_remove(ctx, msg_filter, words, channel=False):
    '''
    Removes the words from the filter for the channel or guild
    '''

    guild_id = str(ctx.guild.id)
    words_removed = False

    # Check if the guild is filter
    if guild_id in msg_filter:
        # Check if we are removing for the channel or guild filter
        if channel:
            channel_id = str(ctx.channel.id)

            # Check if there is anything in the channel filter
            if channel_id in msg_filter[guild_id]['channels']:
                # Loop over the words in the channel filter
                for word in words:
                    word = word.lower()
                    if word not in msg_filter[guild_id]['channels'][channel_id]:
                        continue
                    else:
                        msg_filter[guild_id]['channels'][channel_id].remove(word)
                        words_removed = True
                
                # Check if the current channel filter is empty
                if msg_filter[guild_id]['channels'][channel_id]:
                    msg_filter[guild_id]['channels'].pop(channel_id)
            else:
                await ctx.send((f'{ctx.author.mention}, '
                                'Nothing is being filtered in this channel '
                                '(except server wide filter)'))
                return msg_filter
        else:
            # Check if anything is being filtered guild wide
            if msg_filter[guild_id]['server']:
                # Loop over the words it check to be removed
                for word in words:
                    word = word.lower()
                    if word not in msg_filter[guild_id]['server']:
                        continue
                    else:
                        msg_filter[guild_id]['sserver'].remove(word)
                        words_removed = True
            else:
                await ctx.send(f'{ctx.author.mention}, Nothing is being filtered server wide')
                return msg_filter
        
        if words_removed:
            logger.info((f'{ctx.guild.name} ({ctx.guild.id}) '
                         'has removed words from filter'))
            
            # Check if the filter for that server is empty if so remove it
            server_len = len(msg_filter[guild_id]['server'])
            channel_len = len(msg_filter[guild_id]['channels'])
            if server_len == 0 and channel_len == 0:
                msg_filter.pop(guild_id)
                logger.info((f'Guild: {ctx.guild.name} ({ctx.guild.id}) '
                             'has been removed from the filter'))
            
            utils.save_cog_file('mod', 'filter.json', msg_filter)
        
            # Send message saying words have been added
            if channel:
                await ctx.send((f'{ctx.author.mention}, '
                                'Words have been removed from the current channels filter'))
            else:
                await ctx.send((f'{ctx.author.mention}, '
                                'Words have been removed from the server wide filter'))
        return msg_filter
    else:
        await ctx.send('There is nothing being filtered in this guild')
        return msg_filter