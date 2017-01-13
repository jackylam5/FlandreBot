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
                stars = float(data[0]['difficultyrating'])
                maxcombo = 1500
                unsure = False
                try:
                    maxcombo = int(data[0]['max_combo'])
                except:
                    unsure = True
                
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
                
                elif data[0]['mode'] is '3':
                    # osu! Mania                       
                    # Calculate pp
                    
                    ODW = 64 - (3 * od)
                    AccValue = pow((150 / ODW) * pow(int(percent[:-1])/100,16),1.8)*2.5*min(1.15,pow(maxcombo/1500,0.3))
                    StrainBase = pow(5 * max(1, stars/0.0825) - 4, 3)/ 110000 * (1 + 0.1 * min(maxcombo/1500, 1))
                    StrainMult = 1
                    pp = '{0:.2f}pp'.format(pow(pow(AccValue,1.1) + pow(StrainBase * StrainMult, 1.1), (1/1.1)) * 1.1)

                else:
                    # osu! ctb or taiko
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

                # Check for pp
                if pp is not None:
                    if not unsure:
                        osuembed.add_field(name='PP', value='{0} with {1} ({2}).'.format(pp, mods, percent))
                    else:
                        osuembed.add_field(name='PP', value='{0} with {1} ({2}).\nMax Combo is null in osu api (based on 1500 combo)'.format(pp, mods, percent))
                
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
