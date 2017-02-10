import aiohttp
from subprocess import PIPE, STDOUT, Popen
from discord.ext import commands
from discord import Embed, Colour
import re
import math

class osu():
    ''' osu! commands 
    If beatmap link is posted bot will send info on that map
    If the mode is standard the bot will also post the pp you will gain for it (using oppai)
    Mods can be added using + then the mod e.g +DTHD for Double Time + Hidden
    You can also specify the acc by adding it after the mods
    '''
    def __init__(self, bot):
        self.bot = bot
        # Gamemodes based off mode mumber from api
        self.modes = {'0': 'osu!', '1': 'Taiko', '2': 'CtB', '3': 'osu!mania'}
        # Map Ranking status based off number from api
        self.map_status = {'-2': 'Graveyard', '-1': 'WIP','0': 'Pending', '1': 'Ranked', '2': 'Approved', '3': 'Qualified', '4': 'Loved'}

    async def getBeatmap(self, message):
        ''' Get Beatmap Info '''
        if 'osu' not in message.channel.name.lower():
            return

        words = message.content.split(' ')
        mods = ''
        percent = ''
        score = ''
        sr = ''
        comb = ''
        mis = ''
        url = None

        for word in words:
            if 'osu.ppy.sh/b/' in word:
                # Get map and make request url
                mapID = word.split('/b/')[1].split('&')[0] 
                url = 'https://osu.ppy.sh/api/get_beatmaps?k={0}&b=' + str(mapID)
                beatmapSet = False
            
            elif 'osu.ppy.sh/s/' in word:
                # Get mapset and make request url
                mapID = word.split('/s/')[1]
                url = 'https://osu.ppy.sh/api/get_beatmaps?k={0}&s=' + str(mapID)
                beatmapSet = True 
            
            elif '+' in word:
                mods = word.upper()
            
            elif '%' in word:
                percent = word   
                
            elif 'sr' in word.lower():
                sr = word
            
            elif 'score' in word.lower() or 'sc' in word.lower():
                score = word
        
            elif 'combo' in word.lower() or 'c' in word.lower():
                comb = word
        
            elif 'miss' in word.lower() or 'm' in word.lower():
                mis = word
        
        #custom starrating (for DT)
        counter = 0
        doneCounting = False
        srtext = ''
                
        for char in sr:
            try:
                if char == '.':
                    doneCounting = True
                checkchar = int(char)
                srtext = srtext + str(checkchar)
                if doneCounting:
                    counter += 1
            except:
                pass
        
        srcalc = 0
        if srtext != '':
            if doneCounting:
                counter = pow(10, counter)
                srcalc = int(srtext)/counter
            else:
                srcalc = int(srtext)
            
        #custom score (mania only)
        scoretext = ''
        for char in score:
            try:
                checkchar = int(char)
                scoretext = scoretext + str(checkchar)
            except:
                pass
        
        score = 1000000
        
        if scoretext != '':
            scorecalc = int(scoretext)
            if scorecalc > 0 and scorecalc < 1000000:
                score = scorecalc
        
            
        
        #fix percent
        acctext = ''
        getacc = percent + mods
        counter = 0
        doneCounting = False
        
        for char in getacc:
            try:
                if char == '.':
                    doneCounting = True
                checkchar = int(char)
                acctext = acctext + str(checkchar)
                if doneCounting:
                    counter += 1
            except:
                pass
        
        acccalc = 100
        if acctext != '':
            if doneCounting:
                counter = pow(10, counter)
                acccalc = int(acctext)/counter
            else:
                acccalc = int(acctext)
                
        if acccalc > 0 and acccalc < 100:               
            percent = str(acccalc) + '%'
        else:
            percent = '100%'
        
        #get combo
        
        combo = 0
        combotext = ''
        for char in comb:
            try:
                checkchar = int(char)
                combotext = combotext + str(checkchar)
            except:
                pass
        
        if combotext != '':
            combo = int(combotext)
        
        #get miss
        
        misstext = ''
        for char in mis:
            try:
                checkchar = int(char)
                misstext = misstext + str(checkchar)
            except:
                pass
        
        miss = 0
        if misstext != '':
            miss = int(misstext)
        
        #get mods
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
        
        # Get Api Info
        with aiohttp.ClientSession() as aioclient:
            async with aioclient.get(url.format(self.bot.config['osukey'])) as resp:
                data = await resp.json()
                status_code = resp.status

        # Check if there is data and the request was sucessful
        if data and status_code == 200:
            # Set discord embed colour, beatmap(s) state, split length into mins and seconds
            colour = Colour(16738740)
            state = self.map_status[data[0]['approved']]  
            m, s = divmod(int(data[0]['total_length']), 60)
            # Create Embed
            osuembed = Embed(type='rich', colour=colour)
            
            if beatmapSet:
                # Beatmap Set
                # Add embed fields
                osuembed.add_field(name='Artist', value=data[0].get('artist', 'Unknown'))
                osuembed.add_field(name='Creator', value=data[0].get('creator','Unknown'))
                osuembed.add_field(name='BPM', value=data[0].get('bpm', 'Unknown'))
                # Check for a source
                if data[0]['source']:
                    osuembed.add_field(name='Source', value=data[0].get('source', 'Unknown'))
                else:
                    osuembed.add_field(name='Source', value='Unknown')
                osuembed.add_field(name='State', value=state)
                length = str(m) + ':'+ str(s) + 's'
                osuembed.add_field(name='Length', value=length)
                
                # Get each difficulty name and make it into a nice string
                diffs = []
                for diff in data:
                    diffs.append(diff['version'])

                osuembed.add_field(name='Difficulties', value=', '.join(diffs))
            
            else:
                # BeatMap
                # Get stars and max combo (set to 1500 if not found)
                stars = 0
                if srcalc == 0:
                    stars = float(data[0]['difficultyrating'])
                else:
                    stars = srcalc
                
                unsure = False
                if combo == 0:
                    maxcombo = 1500
                    try:
                        maxcombo = int(data[0]['max_combo'])
                    except:
                        unsure = True
                else:
                    maxcombo = combo
                # Get cs, od , ar and hp 
                cs = float(data[0]['diff_size'])
                od = float(data[0]['diff_overall'])
                ar = float(data[0]['diff_approach'])
                hp = float(data[0]['diff_drain'])
                
                if data[0]['mode'] is '0':
                    # osu! std
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
                
                elif data[0]['mode'] is '1':
                    # osu! Taiko
                    # Calculate pp

                    #OD Calculation
                    
                    #if HR is used
                    
                    if 'HR' in mods:
                        od = od * 1.4
                    
                    #Get hitwindow Value of OD
                    odround = math.floor(od)
                    oddec = od - odround

                    ODW = 49.5 - (3*odround)
                    
                    if oddec > 0 and oddec < 0.34:
                        ODW = ODW - 1
                    elif oddec >= 0.34 and oddec < 0.67:
                        ODW = ODW - 2
                    elif oddec >=0.67:
                        ODW = ODW - 3
                    
                    #DT changes hitwindow
                    
                    if 'DT' in mods:
                        ODW = ODW / 1.5
                    
                    #get acc
                    acccalc = acccalc/100
                    
                    #get strainValue for pp
                    strainValue = pow(5 * max(1, stars/0.0075) - 4, 2) / 100000 * 1 * (1 + 0.1 * min(maxcombo/1500, 1)) * pow(0.985, miss) * acccalc * min(pow(maxcombo-miss,0.5) / pow(maxcombo, 0.5), 1)
                    
                    #Check if HD or FL is used for bonus pp
                    if 'HD' in mods:
                        strainValue = strainValue * 1.025
                    if 'FL' in mods:
                        strainValue = strainValue * 1.05 * 1 * (1 + 0.1 * min(maxcombo/1500, 1))
                        
                    #accValue for pp    
                    accValue = pow(150 / ODW, 1.1) * pow(acccalc, 15) * 22 * min(1.15, pow(maxcombo / 1500, 0.3))
                    
                    #PP value
                    totalValue = pow(pow(strainValue, 1.1) + pow(accValue, 1.1) , (1/1.1)) * 1.1
                    
                    #PP increase with some mods
                    if 'NF' in mods:
                        totalValue = totalValue * 0.9
                    if 'HD' in mods:
                        totalValue = totalValue * 1.1
                        
                    pp = '{0:.2f}pp'.format(totalValue)

                elif data[0]['mode'] is '2':

                    # osu! ctb
                    # Get beatmap for PP 

                    #get accuracy
                    acccalc = acccalc / 100
                    
                    #Calculates Aim Value of map
                    aimValue = pow(5 * max(1, stars/0.0049) - 4, 2) / 100000
                    
                    #Bonus pp for long maps
                    lengthBonus = 0.95 + 0.4 * min(1, maxcombo/3000)
                    
                    #check if HR is used for AR increase
                    if 'HR' in mods:
                        ar = ar * 1.4
                        if ar > 10:
                            ar = 10
                    
                    if 'DT' in mods:
                        ar = 5 + ((ar - 1) * 2/3)
                        if ar > 11:
                            ar = 11
                    #Bonus pp for AR higher than 9 or lower than 8
                    ARValue = 1
                    if ar > 9:
                        ARValue = 1 + 0.1 * (ar-9)
                    elif ar < 8:
                        ARValue = 1 + 0.025 * (8 - ar)
                        
                    #Using mods gives bonus pp
                    bonus = 1
                    
                    if 'HD' in mods:
                        bonus = bonus * 1.05 + 0.075 * (10 - min(10, ar))
                    
                    if 'FL' in mods:
                        bonus = bonus * 1.35 * lengthBonus
                        
                    if 'NF' in mods:
                        bonus = bonus * 0.9
                    
                    #pp calculation
                    accValue = pow(acccalc, 5.5)
                    
                    aimTotal = aimValue * lengthBonus * ARValue * bonus
                    
                    pp = '{0:.2f}pp'.format(aimTotal * accValue)
                
                elif data[0]['mode'] is '3':
                    # osu! Mania                       
                    # Calculate pp
                    
                    #hitWindow of OD
                    ODW = 64 - (3 * od)
                    
                    #accValue for pp
                    AccValue = pow((150 / ODW) * pow(acccalc/100,16),1.8)*2.5*min(1.15,pow(maxcombo/1500,0.3))
                    
                    #strainBase for pp
                    StrainBase = pow(5 * max(1, stars/0.0825) - 4, 3)/ 110000 * (1 + 0.1 * min(maxcombo/1500, 1))
                    
                    #Multiplier based on score
                    StrainMult = 0
                    if score <= 500000:
                        StrainMult = 0;
                    elif score > 500000 and score <= 600000:
                        StrainMult = (score - 500000)/ 100000 * 0.3
                    elif score > 600000 and score <= 700000:
                        StrainMult = 0.3 + (score - 600000) / 100000 * 0.35
                    elif score > 700000 and score <= 800000:
                        StrainMult = 0.65 + (score - 700000) / 100000 * 0.2
                    elif score > 800000 and score <= 900000:
                        StrainMult = 0.85 + (score - 800000) / 100000 * 0.1
                    else:
                        StrainMult = 0.95 + (score - 900000) / 100000 * 0.05
                    
                    #pp Value
                    pp = '{0:.2f}pp'.format(pow(pow(AccValue,1.1) + pow(StrainBase * StrainMult, 1.1), (1/1.1)) * 1.1)

                else:
                    # non existent mode
                    pp = None 
                
                if mods != '':
                    mods = mods.replace('+', '')
                else:
                    mods = 'No Mods'
                           
                osuembed.add_field(name='Artist', value=data[0].get('artist', 'Unknown'))
                osuembed.add_field(name='Creator', value=data[0].get('creator','Unknown'))
                osuembed.add_field(name='BPM', value=data[0].get('bpm', 'Unknown'))
                # Check for a source
                if data[0]['source']:
                    osuembed.add_field(name='Source', value=data[0].get('source', 'Unknown'))
                else:
                    osuembed.add_field(name='Source', value='Unknown')
                osuembed.add_field(name='State', value=state)
                length = str(m) + ':'+ str(s) + 's'
                osuembed.add_field(name='Length', value=length)
                osuembed.add_field(name='Stars', value='{0:.2f}★'.format(stars))
                osuembed.add_field(name='Max Combo', value=maxcombo)
                osuembed.add_field(name='CS', value='{0:.2f}'.format(cs))
                osuembed.add_field(name='OD', value='{0:.2f}'.format(od))
                osuembed.add_field(name='AR', value='{0:.2f}'.format(ar))
                osuembed.add_field(name='HP', value='{0:.2f}'.format(hp))
                if data[0]['mode'] is '3':
                    osuembed.add_field(name='Score', value='{}'.format(score))
                elif data[0]['mode'] is '1':
                    osuembed.add_field(name='Miss', value='{}'.format(miss))
                # Check for pp
                if pp is not None:
                    if not unsure:
                        osuembed.add_field(name='PP', value='{0} with {1} ({2}).'.format(pp, mods, percent))
                    else:
                        osuembed.add_field(name='PP', value='{0} with {1} ({2}).'.format(pp, mods, percent))
                        osuembed.add_field(name='Note', value='Max Combo is null in osu api (based on 1500 combo).\nPlease add max combo behind the link for example: C1337'.format(pp, mods, percent))
                    
                    if 'DT' in mods:
                        osuembed.add_field(name='About DT', value='Please add star rating behind the link for example: SR5.63.')
                osuembed.add_field(name='Downloads', value='[Website](https://osu.ppy.sh/d/{0})\n[Direct](osu://dl/{0})'.format(data[0]['beatmapset_id']), inline=False)
                osuembed.set_footer(text='Mode: {0}'.format(self.modes[data[0]['mode']]))

            # Set thumbnail to map background and title to map name 
            osuembed.set_thumbnail(url='https://b.ppy.sh/thumb/'+ data[0]['beatmapset_id'] + '.jpg')
            osuembed.set_author(name=data[0]['title'], url='https://osu.ppy.sh/s/' + data[0]['beatmapset_id'], icon_url='https://b.ppy.sh/thumb/'+ data[0]['beatmapset_id'] + '.jpg')
            await self.bot.send_message(message.channel, embed=osuembed)
        else:
            await self.bot.send_message(message.channel, 'osu! API seems to be down right now. Try again later')

    async def on_osu_message(self, message):
        ''' Check if beatmap was sent '''
        if '/osu.ppy.sh/s/' in message.content.lower() or '/osu.ppy.sh/b/' in message.content.lower():
            if message.author != self.bot.user and not message.author.bot:
                await self.getBeatmap(message)

def setup(bot):
    n = osu(bot)
    bot.add_listener(n.on_osu_message, "on_message")
    bot.add_cog(n)
