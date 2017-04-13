import discord
import aiohttp
from subprocess import PIPE, STDOUT, Popen
from discord.ext import commands
from FlandreBot.utils.IO import files
from FlandreBot.utils import permissions
from FlandreBot.cogs.osu import osu
import os
import time
import json
import re
import asyncio

server = 'irc.chat.twitch.tv'
port = '6667'

class irc:
    
    def __init__(self, bot):
        self.bot = bot
        self.channels = files("FlandreBot/data/irc/channels.json", "load")
        self.config = files("FlandreBot/data/irc/config.json", "load")
        self.loop = asyncio.get_event_loop()
        
        self.modes = {'0': 'osu!', '1': 'Taiko', '2': 'CtB', '3': 'osu!mania'}
        self.map_status = {'-2': 'Graveyard', '-1': 'WIP','0': 'Pending', '1': 'Ranked', '2': 'Approved', '3': 'Qualified', '4': 'Loved'}
        self.writer = None
        self.reader = None
        self.setup()
        
    def setup(self):
        self.loop.create_task(self.loginIRC())
        
    def loginIRC(self):
        self.reader, self.writer = yield from asyncio.open_connection(
                server, port, loop=self.loop)
        self.writer.write("PASS {}\r\n".format(self.config['token']).encode('utf-8'))
        self.writer.write("NICK {}\r\n".format(self.config['user']).encode('utf-8'))
        self.writer.write("JOIN {}\r\n".format(self.config['channel']).encode('utf-8'))
        print("done!")
        self.loop.create_task(self.getMessage())
        
    async def getMessage(self):
        while True:
            data = (await self.reader.readline()).decode("utf-8").strip()
            if not data:
                continue
            
            if 'You are in a maze of twisty passages' in data:
                continue
            
            if 'https://osu.ppy.sh/b/' in data:
                print("nice")
                message = await self.getBeatmap(data)
                await self.sayIRC(self.config['channel'], message)
                
            if '{}skin'.format(self.config['prefix']) in data:
                await self.sayIRC(self.config['channel'], 'Eigen skin v8: https://puu.sh/v8ryq.osk')
                

                
            print(data)

    async def sayIRC(self, channel, s):
        '''send message'''
        s = s.replace("\n", " ")
        self.writer.write("PRIVMSG {} :{}\r\n".format(
            channel, s).encode('utf-8'))
                
    @commands.group(name="irc", pass_context=True)
    @permissions.checkOwner()
    async def _irc(self, ctx):
        """Bot settings"""
        if ctx.invoked_subcommand is None:
            pages = self.send_cmd_help(ctx)
            for page in pages:
                await self.bot.send_message(ctx.message.channel, page)
                
    @_irc.command(pass_context=True)
    async def ping(self, ctx):
        """Change bot's prefix"""
        await self.sayIRC(self.config['channel'], 'pong!')

    @_irc.command(pass_context=True)
    async def say(self, ctx, *message):
        message = " ".join(message)
        """Change bot's prefix"""
        if len(message) > 499:
            await self.bot.say('Message is too long')
            return
            
        await self.sayIRC(self.config['channel'], message)
            
    async def getBeatmap(self, message):
        ''' Get Beatmap Info '''
        with open('FlandreBot/data/osu/namefix.json', 'r') as file:
            self.namefix = json.load(file)

        words = message.split(' ')
        mods = ''
        percent = ''
        score = ''
        sr = ''
        comb = ''
        mis = ''
        url = None
        miss = 0
        combo = 0
        
        for word in words:
            if 'osu.ppy.sh/ss/' in word:
                with aiohttp.ClientSession() as aioclient:
                    async with aioclient.get(word) as resp:
                        data = await resp.read()
                im = io.BytesIO(data)
                image = Image.open(im)
                width = image.size[0]
                height = image.size[1]
                image = image.crop((0, 0, width, height/8))
                beatmapText = pytesseract.image_to_string(image)
                del im
                beatmapText = beatmapText.split("-")
                mapText = ""
                userText = ""
                foundPlayer = False
                counter = 0
                counter = 0
                for text in beatmapText:
                    if counter < 1:
                        counter += 1
                    if 'by' in text and not foundPlayer:
                        userText = text.split("Played")
                        userText = userText[1][3:]
                        userText = userText.split("on")
                        userText = userText[0][:-1]
                        foundplayer = True
                mapNameText = beatmapText[0].split(" ")
                
                mapNameText = mapNameText[0]
                
                if userText[:1] == ' ':
                    userText = userText[1:]
                    
                if userText in self.namefix:
                    userText = self.namefix[userText]['name']
                
                testTextTest = mapNameText + " | " + userText

                if 'debug' in message.lower():
                    await self.bot.send_message(message.channel, testTextTest)
                
                getUserUrl = "https://osu.ppy.sh/api/get_user?k={0}&u={1}"
                
                with aiohttp.ClientSession() as aioclient:
                    async with aioclient.get(getUserUrl.format(self.config['apiKey'], userText)) as resp:
                        data = await resp.json()
                
                try:
                    events = data[0]['events']
                    beatmapID = None
                    for maps in events:
                        if mapNameText in maps['display_html']:
                           beatmapID = maps['beatmap_id'] 
                           
                except:
                    return
                    
                if beatmapID == None:
                    return
                    
                if 'test2' in message.lower():
                    await self.bot.send_message(message.channel, testTextTest)

                getScoreUrl = "https://osu.ppy.sh/api/get_user_recent?k={0}&u={1}"
                with aiohttp.ClientSession() as aioclient:
                    async with aioclient.get(getScoreUrl.format(self.config['apiKey'], userText)) as resp:
                        data = await resp.json()
                    
                try:
                    scores = data
                    for score in scores:
                        if score['beatmap_id'] == beatmapID:
                            mapID = beatmapID
                            url = 'https://osu.ppy.sh/api/get_beatmaps?k={0}&b=' + beatmapID
                            beatmapSet = False
                            miss = int(score['countmiss'])
                            combo = int(score['maxcombo'])
                            count300 = int(score['count300'])
                            count100 = int(score['count100'])
                            count50 = int(score['count50'])
                            accNow = (count300 * 1) + (count100 * (1/3)) + (count50 * (1/6)) 
                            accTotal = accNow  / (count300 + count100 + count50 + miss)
                            percent = '{0:.2f}%'.format(accTotal * 100)
                            mods = '+' + self.getModFromInt(int(score['enabled_mods']))
                            break
                            
                except:
                    return
                
                if url == None:
                    return
                
                break;
                        
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
            async with aioclient.get(url.format(self.config['apiKey'])) as resp:
                data = await resp.json()
                status_code = resp.status

        # Check if there is data and the request was sucessful
        if data and status_code == 200:
            # Set discord embed colour, beatmap(s) state, split length into mins and seconds
            state = self.map_status[data[0]['approved']]  
            m, s = divmod(int(data[0]['total_length']), 60)
            # Create Embed
            
            if beatmapSet:
                pass
            
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
                    if combo != 0 and miss != 0:
                        if mods != '':
                            proc = Popen(['./oppai', '-', mods, percent, str(combo) + 'x', str(miss) + 'm'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                        else:
                            proc = Popen(['./oppai', '-', percent, str(combo) + 'x', str(miss) + 'm'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                    elif miss == 0 and combo != 0 and mods != '':
                        proc = Popen(['./oppai', '-', mods, percent, str(combo) + 'x'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
                    elif miss == 0 and combo == 0 and mods != '':
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
                    
                message = ""
                
                
                if data[0]['artist']:
                    message = message + " Artist: " + data[0].get('artist', 'Unknown')
                else:
                    message = message + " Artist: Unknown"
                message = message + " Creator: " + data[0].get('creator','Unknown')
                message = message + " BPM: " + data[0].get('bpm', 'Unknown')

                # Check for a source
                if data[0]['source']:
                    message = message + " Source: " + data[0].get('source', 'Unknown')
                else:
                    message = message + " Source: Unknown"
                    
                message = message + " State: " + state
                length = str(m) + ':'+ str(s) + 's'
                message = message + " Length: " + length
                message = message + " Stars: " + '{0:.2f}★'.format(stars)
                message = message + " Max Combo: " + str(maxcombo)
                message = message + " CS: " + '{0:.2f}'.format(cs)
                message = message + " OD: " + '{0:.2f}'.format(od)
                message = message + " AR: " + '{0:.2f}'.format(ar)
                message = message + " HP: " + '{0:.2f}'.format(hp)
                message = message + " State: " + state
                message = message + " State: " + state
                message = message + " PP: " + '{0} with {1} ({2}).'.format(pp, mods, percent)
                message = message + ' Mode: {0}'.format(self.modes[data[0]['mode']])
                message = message[1::]
                try:
                    return message
                except Exception as e:
                    print("Unknown Exception: {}".format(e))

            
    #help message
    def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = self.bot.formatter.format_help_for(ctx, ctx.invoked_subcommand)
            return pages
        else:
            pages = self.bot.formatter.format_help_for(ctx, ctx.command)
            return pages  

def check_folders():
    if not os.path.exists("FlandreBot/data/irc"):
        print("Creating FlandreBot/data/irc folder...")
        os.makedirs("FlandreBot/data/irc")

def check_files():
    if not os.path.isfile("FlandreBot/data/irc/channels.json"):
        print("Creating empty channels.json...")
        files("FlandreBot/data/irc/channels.json", "save", {})
    if not os.path.isfile("FlandreBot/data/irc/config.json"):
        print("Creating empty config.json...")
        files("FlandreBot/data/irc/config.json", "save", {"user" : "username", "token" : "oauth token", "channel" : "default channel", "prefix" : "!"})

def setup(bot):
    check_folders()
    check_files()
    n = irc(bot)
    bot.add_cog(n)