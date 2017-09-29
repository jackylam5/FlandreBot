'''
Holds the filter functions
'''
import logging
import re
import discord

from Flandre import utils

logger = logging.getLogger(__package__)

CLEANUP_REG = re.compile('[`*~_\u200B]+')

FILTER_MSG = ('Hey {0.author.name}, Your message in **{0.guild.name}** '
              'was deleted. This because it contained `{1}` which is filtered there.')

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
        msg_filter[guild_id] = {'server': [], 'channels': {}}
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

def check_immune(message):
    '''
    Check if the user has the Manage Guild or Manage Channel permission
    If they do their message will not be filtered
    '''

    if message.author.bot and message.author != message.guild.me:
        return False

    else:
        if message.channel.permissions_for(message.author).manage_guild:
            return True
        elif message.channel.permissions_for(message.author).manage_channels:
            return True
        else:
            return False

def find_filtered_word(word, content):
    '''
    Finds the given word in the content using regex
    '''

    word = re.escape(word)
    cleaned_message = CLEANUP_REG.sub('', content)
    found = re.search(f'\\b{word}\\b', cleaned_message, re.IGNORECASE)

    return found

async def check_filter(message, msg_filter):
    '''
    Check if the message contains a filtered word for that guild
    Returns True if the message was removed else will return False
    '''

    guild_id = str(message.guild.id)
    channel_id = str(message.channel.id)

    # Check that the message was sent in a guild channel and not a DM
    if isinstance(message.channel, discord.abc.GuildChannel):
        # Check if the bot has the permission to delete messages
        if message.channel.permissions_for(message.guild.me).manage_messages:
            if guild_id in msg_filter:
                if not check_immune(message):
                    to_check = f'{message.content}\n'

                    # Get embed content
                    if message.embeds:
                        for embed in message.embeds:
                            embed_dict = embed.to_dict()
                            to_check += 'Title: {}\n'.format(embed_dict.get('title', ''))
                            to_check += 'Desc: {}\n'.format(embed_dict.get('description', ''))

                            if 'fields' in embed_dict:
                                to_check += 'Fields: '
                                for field in embed_dict['fields']:
                                    to_check += '{}\n'.format(field.get('name', ''))
                                    to_check += '{}\n'.format(field.get('value', ''))

                    # Check guild filter
                    for word in msg_filter[guild_id]['server']:
                        found = find_filtered_word(word, to_check)

                        # If re found the word delete the message and tell the user if that was set up
                        if found is not None:
                            try:
                                await message.delete()
                            except discord.errors.NotFound:
                                logger.warning(f'Message ({message.id}) has already been deleted')
                                return False

                            # Try to DM the user why their message was filtered
                            try:
                                await message.author.send(FILTER_MSG.format(message, word))
                            except:
                                pass

                            return True

                    else:
                        # Check the channel filter since guild wide did not filter it
                        if channel_id in msg_filter[guild_id]['channels']:
                            for word in msg_filter[guild_id]['channels'][channel_id]:
                                found = find_filtered_word(word, to_check)

                                if found is not None:
                                    try:
                                        await message.delete()
                                    except discord.errors.NotFound:
                                        logger.warning(f'Message ({message.id}) has already been deleted')
                                        return False

                                    # Try to DM the user why their message was filtered
                                    try:
                                        await message.author.send(FILTER_MSG.format(message, word))
                                    except:
                                        pass

                                return True

    return False
