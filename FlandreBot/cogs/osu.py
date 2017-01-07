import aiohttp
from subprocess import PIPE, STDOUT, Popen
from discord import Embed, Colour

class osu():
    ''' osu! commands 
    If beatmap link is posted bot will send info on that map
    If the mode is standard the bot will also post the pp you will gain for it (using oppai)
    Mods can be added using + then the mod e.g +DTHD for Double Time + Hidden
    You can also specify the acc by adding it after the mods
    '''
    def __init__(self, bot):
        self.bot = bot
        self.modes = {0: 'osu!', 1: 'Taiko', 2: 'CtB', 3: 'osu!mania'}

    def mapStatus(self, status):
        ''' Return is a map is ranked and that '''
        if status == '0':
            return 'Pending'
        elif status == '-1':
            return 'WIP'
        elif status == '-2':
            return 'Graveyard'
        elif status == '1':
            return 'Ranked'
        elif status == '2':
            return 'Approved'
        elif status == '3':
            return 'Qualified'
        elif status == '4':
            return 'Loved'

    async def getBeatmap(self, message):
        ''' Get Beatmap Info '''
        words = message.content.split(' ')
        mods = ''
        percent = '100%'
        mode = 0
        for word in words:
            if 'osu.ppy.sh/b/' in word:
                osu_link = word
                beatmapSet = False
                mode = osu_link.split('&m=')[1]
            elif 'osu.ppy.sh/s/' in word:
                osu_link = word
                beatmapSet = True
            elif '+' in word:
                mods = word.upper()
            elif '%' in word:
                percent = word

        # Get request url
        if beatmapSet:
            # Beatmap Set
            mapID = osu_link.split('/s/')[1]
            url = 'https://osu.ppy.sh/api/get_beatmaps?k={0}&s=' + str(mapID)
        else:
            # Single Map
            mapID = osu_link.split('/b/')[1].split('&')[0] 
            url = 'https://osu.ppy.sh/api/get_beatmaps?k={0}&b=' + str(mapID)

        # Get beatmap Info
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(url.format(self.bot.config['osukey'])) as resp:
                data = await resp.json()

        if data:
            colour = Colour(16738740)
            rank = self.mapStatus(data[0]['approved'])       
            m, s = divmod(int(data[0]['total_length']), 60)
            if beatmapSet:
                desc = ('Artist: {0[0][artist]}\n'
                        'Creator: {0[0][creator]}\n'
                        'BPM: {0[0][bpm]}\n'
                        'Source: {0[0][source]}\n'
                        'State: {1}\n'
                        'Length: {2}:{3}\n'
                        'Number of difficulties: {4}'
                        )
                embed = Embed(type='rich', description=desc.format(data, rank, m, s, len(data)), colour=colour)
            else:
                stars = float(data[0]['difficultyrating'])
                cs = float(data[0]['diff_size'])
                od = float(data[0]['diff_overall'])
                ar = float(data[0]['diff_approach'])
                hp = float(data[0]['difficultyrating'])

                if int(mode) is 0:
                    # Get beatmap for PP 
                    with aiohttp.ClientSession() as aioclient:
                        async with aioclient.get('http://osu.ppy.sh/osu/' + mapID) as resp:
                            beatmap = await resp.read()

                    # Use oppai to get pp
                    if mods != '':
                        proc = Popen(['./oppai', '-', mods, percent], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                    else:
                        proc = Popen(['./oppai', '-', percent], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                    
                    stdout, stderr = proc.communicate(beatmap)
                    proc.kill()
                    del beatmap
                    pp = stdout.decode().split('\n')[-2].strip()
                
                if mods != '':
                    mods = mods.replace('+', '')
                else:
                    mods = 'No Mods'
            
                desc = ('Artist: {0[0][artist]}\n'
                        'Creator: {0[0][creator]}\n'
                        'Difficulty: {0[0][version]}\n'
                        'BPM: {0[0][bpm]}\n'
                        'Source: {0[0][source]}\n'
                        'State: {1}\n'
                        'Length: {2}:{3}\n'
                        'Stars: {4:.2f}★\n'
                        'CS: {5:.2f}\n'
                        'OD: {6:.2f}\n'
                        'AR: {7:.2f}\n'
                        'HP: {8:.2f}\n'
                        )
                if int(mode) is 0:
                    desc += 'PP: {9} with {10} ({11})'
                    embed = Embed(type='rich', description=desc.format(data, rank, m, s, stars, cs, od, ar, hp, pp, mods, percent), colour=colour)
                else:
                    desc += 'PP: Cannot be calculated using oppai'
                    embed = Embed(type='rich', description=desc.format(data, rank, m, s, stars, cs, od, ar, hp), colour=colour)
                embed.set_footer(text='Mode: {0}'.format(self.modes[int(mode)]))

            embed.set_thumbnail(url='https://b.ppy.sh/thumb/'+ data[0]['beatmapset_id'] + '.jpg')
            embed.set_author(name=data[0]['title'], url='https://osu.ppy.sh/s/' + data[0]['beatmapset_id'], icon_url='https://b.ppy.sh/thumb/'+ data[0]['beatmapset_id'] + '.jpg')
            await self.bot.send_message(message.channel, embed=embed)

    async def on_message(self, message):
        ''' Check if beatmap was sent '''
        if '/osu.ppy.sh/s/' in message.content.lower() or '/osu.ppy.sh/b/' in message.content.lower():
            await self.getBeatmap(message)

def setup(bot):
    n = osu(bot)
    bot.add_listener(n.on_message, "on_message")
    bot.add_cog(n)
