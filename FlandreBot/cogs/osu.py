import aiohttp
from subprocess import PIPE, STDOUT, Popen
from discord import Embed, Colour
import re

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
        if 'osu' not in message.channel.name.lower():
            return
        ''' Get Beatmap Info '''
        words = message.content.split(' ')
        mods = ''
        percent = 'Fill'
        mode = 0
        for word in words:
            if 'osu.ppy.sh/b/' in word:
                osu_link = word
                beatmapSet = False
                mode = osu_link.split('m=')[1]
            elif 'osu.ppy.sh/s/' in word:
                osu_link = word
                beatmapSet = True 
            elif '+' in word:
                mods = word.upper()
            elif '%' in word:
                percent = word   
        
        #fix percent
        acctext = ''
        getacc = percent + mods
        
        for char in getacc:
            try:
                checkchar = int(char)
                acctext = acctext + str(checkchar)
            except:
                pass
                
        
        if acctext != '':
            accnumber = int(acctext)
            if percent != '100%':
                if accnumber < 0:
                    percent = '0%'
                elif accnumber > 100:
                    percent = '100%'
                else:
                    percent = acctext + '%'
        else:
            percent = '100%'
            
        if '+' + percent == mods:
            mods = ''
        
        modslist = {'HD', 'HR', 'DT', 'FL', 'HT', 'EZ', 'SO', 'NF'}
        checkmods = re.findall('..?', mods[1:])
        mods = ''
        for checkmod in checkmods:
            if checkmod in modslist:
                mods = mods + checkmod
        
        if mods != '':
            mods = '+' + mods
        
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
                maxcombo = 0
                unsure = False
                try:
                    maxcombo = int(data[0]['max_combo'])
                except:
                    maxcombo = 1500
                    unsure = True
                cs = float(data[0]['diff_size'])
                od = float(data[0]['diff_overall'])
                ar = float(data[0]['diff_approach'])
                hp = float(data[0]['difficultyrating'])
                if int(data[0]['mode']) is 0:
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
                
                if int(data[0]['mode']) is 3:
                    # Get beatmap for PP
                    with aiohttp.ClientSession() as aioclient:
                        async with aioclient.get('http://osu.ppy.sh/osu/' + mapID) as resp:
                            beatmap = await resp.read()
                       
                    # Calculate pp
                    
                    ODW = 64 - (3 * od)
                    AccValue = pow((150 / ODW) * pow(int(percent[:-1])/100,16),1.8)*2.5*min(1.15,pow(maxcombo/1500,0.3))
                    StrainBase = pow(5 * max(1, stars/0.0825) - 4, 3)/ 110000 * (1 + 0.1 * min(maxcombo/1500, 1))
                    StrainMult = 1
                    pp = pow(pow(AccValue,1.1) + pow(StrainBase * StrainMult, 1.1), (1/1.1)) * 1.1
                
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
                        'Max Combo: {5}\n'
                        'CS: {6:.2f}\n'
                        'OD: {7:.2f}\n'
                        'AR: {8:.2f}\n'
                        'HP: {9:.2f}\n'
                        )
                if int(data[0]['mode']) is 0:
                    desc += 'PP: {10} with {11} ({12})'
                    embed = Embed(type='rich', description=desc.format(data, rank, m, s, stars, maxcombo, cs, od, ar, hp, pp, mods, percent), colour=colour)
                elif int(data[0]['mode']) is 3:
                    if unsure:
                        desc += 'PP: {10} with {11} ({12})\nMax Combo is null in osu api (based on 1500 combo)'
                        embed = Embed(type='rich', description=desc.format(data, rank, m, s, stars, maxcombo, cs, od, ar, hp, pp, mods, percent), colour=colour)
                    else:
                        desc += 'PP: {10} with {11} ({12})'
                        embed = Embed(type='rich', description=desc.format(data, rank, m, s, stars, maxcombo, cs, od, ar, hp, pp, mods, percent), colour=colour)
                else:
                    desc += 'PP: Cannot be calculated using oppai'
                    embed = Embed(type='rich', description=desc.format(data, rank, m, s, stars, maxcombo, cs, od, ar, hp), colour=colour)
                embed.set_footer(text='Mode: {0}'.format(self.modes[int(mode)]))

            embed.set_thumbnail(url='https://b.ppy.sh/thumb/'+ data[0]['beatmapset_id'] + '.jpg')
            embed.set_author(name=data[0]['title'], url='https://osu.ppy.sh/s/' + data[0]['beatmapset_id'], icon_url='https://b.ppy.sh/thumb/'+ data[0]['beatmapset_id'] + '.jpg')
            await self.bot.send_message(message.channel, embed=embed)

    async def on_osu_message(self, message):
        ''' Check if beatmap was sent '''
        if '/osu.ppy.sh/s/' in message.content.lower() or '/osu.ppy.sh/b/' in message.content.lower():
            await self.getBeatmap(message)

def setup(bot):
    n = osu(bot)
    bot.add_listener(n.on_osu_message, "on_message")
    bot.add_cog(n)
