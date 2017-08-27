'''
Holds the functions that send messages to the logging channel of the guild
Upon mod actions
'''

import discord

BAN_ACTION = discord.AuditLogAction.ban
KICK_ACTION = discord.AuditLogAction.kick

def create_log_embed(title, target, user, timestamp, reason=None):
    ''' Creates an embed for logging '''

    desc = f'Name: {target.name}\nID: {target.id}'

    # Create embed
    embed = discord.Embed(description=desc, timestamp=timestamp)
    embed.set_author(name=title)
    embed.set_thumbnail(url=target.avatar_url)
    embed.set_footer(text=f'Done by {user.name}', icon_url=user.avatar_url)

    if reason:
        embed.add_field(name='Reason:', value=f'```{reason}```')

    return embed

async def ban_log_message(guild, user, channel):
    '''
    Posts the ban embed to the guilds logging channel
    '''

    def find_banned_user(event):
        ''' Find the event for the banned user '''
        return event.target == user and event.user != guild.me

    # Check the audit log to get who banned the user
    ban_event = await guild.audit_logs(limit=1, action=BAN_ACTION).find(find_banned_user)

    if ban_event:
        embed = create_log_embed('Ban Log',
                                 ban_event.target,
                                 ban_event.user,
                                 ban_event.created_at,
                                 ban_event.reason)

        # Send embed
        await channel.send(embed=embed)

async def kick_log_message(guild, member, channel):
    '''
    Checks if the user was kicked
    If they were make a log message and send it
    '''

    def find_kicked_user(event):
        ''' Find the event for the kicked user '''
        return event.target == member and event.user != guild.me

    # Check the audit log to get who kicked the user
    kick_event = await guild.audit_logs(limit=1, action=KICK_ACTION).find(find_kicked_user)

    if kick_event:
        embed = create_log_embed('Kick Log',
                                 kick_event.target,
                                 kick_event.user,
                                 kick_event.created_at,
                                 kick_event.reason)

        # Send embed
        await channel.send(embed=embed)
