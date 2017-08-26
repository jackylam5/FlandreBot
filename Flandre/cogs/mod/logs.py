'''
Holds the functions that send messages to the logging channel of the guild
Upon mod actions
'''

import discord

BAN_ACTION = discord.AuditLogAction.ban
KICK_ACTION = discord.AuditLogAction.kick

async def ban_log_message(guild, user, channel):
    '''
    Posts the ban embed to the guilds logging channel
    '''

    def find_banned_user(event):
        ''' Find the event for the banned user '''
        return event.target == user

    # Check the audit log to get who banned the user
    ban_event = await guild.audit_logs(limit=5, action=BAN_ACTION).find(find_banned_user)

    if ban_event:
        desc = f'Name: {ban_event.target.name}\nID: {ban_event.target.id}'

        # Create embed
        embed = discord.Embed(type='rich', description=desc, timestamp=ban_event.created_at)
        embed.set_author(name='Ban Log')
        embed.set_thumbnail(url=ban_event.target.avatar_url)
        embed.set_footer(text=f'Done by {ban_event.user.name}', icon_url=ban_event.user.avatar_url)
        
        if ban_event.reason:
            embed.add_field(name='Reason:', value=f'```{ban_event.reason}```')

        # Send embed
        await channel.send(embed=embed)

async def kick_log_message(guild, member, channel):
    '''
    Checks if the user was kicked
    If they were make a log message and send it
    '''

    def find_kicked_user(event):
        ''' Find the event for the kicked user '''
        return event.target == member

    # Check the audit log to get who kicked the user
    kick_event = await guild.audit_logs(limit=5, action=KICK_ACTION).find(find_kicked_user)

    if kick_event:
        desc = f'Name: {kick_event.target.name}\nID: {kick_event.target.id}'

        # Create embed
        embed = discord.Embed(type='rich', description=desc, timestamp=kick_event.created_at)
        embed.set_author(name='Kick Log')
        embed.set_thumbnail(url=kick_event.target.avatar_url)
        embed.set_footer(text=f'Done by {kick_event.user.name}',
                         icon_url=kick_event.user.avatar_url)

        if kick_event.reason:
            embed.add_field(name='Reason:', value=f'```{kick_event.reason}```')

        # Send embed
        await channel.send(embed=embed)
