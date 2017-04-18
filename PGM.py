#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  PGM.py
#  
#  Copyright 2017 Keaton Brown <linux.keaton@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

########################################################################
#   PLANT GIF MAKER                                                    #
########################################################################
# 
# Archiving Jeff's growth through hourly screenshots! Updating on
# Imgur every day, week, and month, automatically!
# 

# Do not include '/u/' or '/r/' in any of these
MY_REDDIT_USER = "Omnipotence_is_bliss"

R_USER = "PlantGifBot"
R_PASS = "REDACTED"
R_CLID = "REDACTED"
R_SCRT = "REDACTED"

I_CLID = "REDACTED"
I_SCRT = "REDACTED"
I_AXSS = "REDACTED"
I_REFR = "REDACTED"
DAY_AL = "rGyhH"
WEK_AL = "3bCHO"
MTH_AL = "aKTcv"

screenshotURL = "https://video.nest.com/api/get_image?uuid=2b5dc4d1a6974df9a44f0bb9bad13216&amp;width=560&quot;"
subreddit = "takecareofmyplant"

## also imports praw, imgurpython, os
from PIL import Image, ImageDraw
from requests import get
from io import BytesIO
import time
import re

# PGM.py is the filename on the RPi
# it is also the filename of the testing file on my laptop
# PGM.pi.py is the version I push to my Pi when I make updates
if __file__.replace("PGM.py","") != __file__:
    filepath = __file__.replace("PGM.py","")
elif __file__.replace("PGM.pi.py","") != __file__:
    filepath = __file__.replace("PGM.pi.py","")
# If it's named anything other than those two, just get the information
# from the filepath from the python command.
else:
    filepath = re.search(r"[a-zA-Z0-9. ]*(.*)",__file__[::-1]).group(1)[::-1]

def getImage():
    # Try 10x to get a good image,
    # if not, wait 5 minutes and
    # try again. Do that 10x.
    ot = 0
    # ot = overall tries
    while ot < 10:
        t = 0
        # t = try
        while t < 10:
            try:
                # Download image
                r = get(screenshotURL)
                # Open it as a PIL Image
                i = Image.open(BytesIO(r.content))
                # Force it to be normal size
                if i.width != 400:
                    i = i.resize((400,224),Image.ANTIALIAS)
                # Initiate drawing
                d = ImageDraw.Draw(i)
                # Add a black box with the date in white
                d.rectangle((0,0,75,12),(0,0,0))
                d.text((3,0),time.strftime("%y-%m-%d-%H",time.gmtime()),(255,255,255))
                # Save it
                i.save(filepath+"dailies/"+time.strftime("%y-%m-%d-%H",time.gmtime())+".jpg")
                # Exit the loops
                return None
            except Exception as e:
                print(e)
                t+=1
        time.sleep(5*60)
        ot += 1

def newOrd(n):
    # Thanks, /u/TylerJayWood
    if 4<=n%100<=20:
        return str(n)+"th"
    else:
        return str(n)+{1:"st",2:"nd",3:"rd"}.get(n%10,"th")

def makeDailyGif(R,Im):
    # Set the time for this operation
    now = time.time()
    ia = []
    # Get the images saved in the folder
    images = [f for f in sorted(os.listdir(filepath+"dailies/")) if f[-3:] == "jpg"]
    for filename in images:
        try:
            # Add PIL Image to image array (ia)
            I = Image.open(filepath+"dailies/"+filename)
            ia.append(I)
        except:
            # That should never fail, but just in case
            continue
    # Set the first picture and save
    first = ia[0]
    first.save(filepath+"dailies/"+time.strftime("%y-%m-%d",time.gmtime(now))+".gif",save_all=True,append_images=[first]+ia,duration=400,loop=0)
    # Get result from previous day
    prevPost = [post for post in R.redditor('takecareofmyplant').submissions.new(limit=2)][1]
    fancyDay = newOrd(int(time.strftime("%-d",time.gmtime(now-24*60*60))))
    if prevPost.title == time.strftime("Today is %A, %B ",time.gmtime(now-24*60*60))+fancyDay+". Do you want to water the plant today?":
        match = re.search(r"Yes \| No\n---\|--\n([0-9]+) \| ([0-9]+)",prevPost.selftext)
        yes = int(match.group(1))
        no = int(match.group(2))
        if yes > no:
            description = "Jeff was watered during this gif."
        else:
            description = "Jeff was not watered during this gif."
    else:
        description = "Failed to find watering result for this day."
    # Upload to imgur
    config = {"album":DAY_AL,"title":time.strftime("%y-%m-%d",time.gmtime(now-24*60*60)),"description":description}
    # Try 30x to upload to imgur
    t=0
    while t<30:
        try:
            uploaded = Im.upload_from_path(filepath+"dailies/"+time.strftime("%y-%m-%d",time.gmtime(now))+".gif",config=config,anon=False)
            break
        except:
            uploaded = False
            t+=1
            time.sleep(2)
    if uploaded:
        # Make reddit post
        rPost = R.subreddit(subreddit).submit("[DPG] Daily Plant Gif for "+time.strftime("%A, %B ",time.gmtime(now-24*60*60))+fancyDay,url=uploaded['link']+"v")
        rPost.reply(description+"\n\n[Click here for more daily plant gifs](https://www.reddit.com/r/"+subreddit+"/search?q=%5BDPG%5D&restrict_sr=on&sort=relevance&t=all)"
                      " or [click here to see them all at once](http://imgur.com/a/"+DAY_AL+")")
        import shutil
        import os
        # Move 3 images to weeklies folder
        saved = [ time.strftime("%y-%m-%d-%H.jpg",time.gmtime(now - i*24/3*60*60)) for i in [0,1,2] ]
        for img in saved:
            try:
                shutil.copy2(filepath+"dailies/"+img,filepath+"weeklies/"+img)
            except:
                continue
        # Move noon image to monthlies folder
        shutil.copy2(filepath+"dailies/"+time.strftime("%y-%m-%d-%H.jpg",time.gmtime(now)),filepath+"monthlies/"+time.strftime("%y-%m-%d-%H.jpg",time.gmtime(now)))
        # Delete all .jpg's in dailies folder
        for f in images:
            os.remove(filepath+"dailies/"+f)
    else:
        R.redditor(MY_REDDIT_USER).message('gif failure','The gif did not upload to imgur and it failed.')

def makeWeeklyGif(R,Im):
    # Check makeDailyGif for annotations on this- it's mostly the same
    import os
    now = time.time()
    ia = []
    images = [f for f in sorted(os.listdir(filepath+"weeklies/")) if f[-3:] == "jpg"]
    for filename in images:
        try:
            I = Image.open(filepath+"weeklies/"+filename)
            ia.append(I)
        except:
            continue
    first = ia[0]
    first.save(filepath+"weeklies/"+time.strftime("%y-%m-%W",time.gmtime(now-24*60*60))+".gif",save_all=True,append_images=[first]+ia,duration=500,loop=0)
    description = "Stills taken from "+time.strftime("%y-%m-%d",time.gmtime(now-6*24*60*60))+" through "+time.strftime("%y-%m-%d",time.gmtime(now))
    config = {"album":WEK_AL,"title":time.strftime("Week ending: %y-%m-%d",time.gmtime(now)),"description":description}
    t = 0
    while t<30:
        try:
            uploaded = Im.upload_from_path(filepath+"weeklies/"+time.strftime("%y-%m-%W",time.gmtime(now))+".gif",config=config,anon=False)
            break
        except:
            uploaded = False
            t+=1
            time.sleep(2)
    if uploaded:
        rPost = R.subreddit(subreddit).submit("[WPG] Weekly Plant Gif for "+time.strftime("%y-%m-%d",time.gmtime(now-6*24*60*60))+" through "+time.strftime("%y-%m-%d",time.gmtime(now)),url=uploaded['link']+"v")
        rPost.reply("[Click here for more weekly plant gifs](https://www.reddit.com/r/"+subreddit+"/search?q=%5BWPG%5D&restrict_sr=on&sort=relevance&t=all)"
                      " or [click here to see them all at once](http://imgur.com/a/"+WEK_AL+")")
        for f in images:
            os.remove(filepath+"weeklies/"+f)
    else:
        R.redditor(MY_REDDIT_USER).message('gif failure','The weekly gif did not upload to imgur and it failed.')

def makeMonthlyGif(R,Im):
    # Check makeDailyGif for annotations on this- it's mostly the same
    import os
    now = time.time()
    ia = []
    images = [f for f in sorted(os.listdir(filepath+"monthlies/")) if f[-3:] == "jpg"]
    for filename in images:
        try:
            I = Image.open(filepath+"monthlies/"+filename)
            ia.append(I)
        except:
            continue
    first = ia[0]
    first.save(filepath+"monthlies/"+time.strftime("%y-%m",time.gmtime(now-24*60*60))+".gif",save_all=True,append_images=[first]+ia,duration=200,loop=0)
    description = "Stills taken from "+time.strftime("%y-%m-%d",time.gmtime(now-29*24*60*60))+" through "+time.strftime("%y-%m-%d",time.gmtime(now))
    config = {"album":MTH_AL,"title":time.strftime("Week ending: %y-%m-%d",time.gmtime(now)),"description":description}
    t = 0
    while t<30:
        try:
            uploaded = Im.upload_from_path(filepath+"monthlies/"+time.strftime("%y-%m",time.gmtime(now-24*60*60))+".gif",config=config,anon=False)
            break
        except:
            uploaded = False
            t+=1
            time.sleep(2)
    if uploaded:
        rPost = R.subreddit(subreddit).submit("[MPG] Monthly Plant Gif for "+time.strftime("%y-%m-%d",time.gmtime(now-29*24*60*60))+" through "+time.strftime("%y-%m-%d",time.gmtime(now)),url=uploaded['link']+"v")
        rPost.reply("[Click here for more monthly plant gifs](https://www.reddit.com/r/"+subreddit+"/search?q=%5BMPG%5D&restrict_sr=on&sort=relevance&t=all)"
                      " or [click here to see them all at once](http://imgur.com/a/"+MTH_AL+")")
        for f in images:
            os.remove(filepath+"monthlies/"+f)
    else:
        R.redditor(MY_REDDIT_USER).message('gif failure','The monthly gif did not upload to imgur and it failed.')

if __name__ == "__main__":
    # Download a stream image every time the script is initiated
    getImage()
    if int(time.strftime("%H",time.gmtime())) == 19:
        import praw
        from imgurpython import ImgurClient
        R = praw.Reddit(client_id=R_CLID,
                        client_secret=R_SCRT,
                        password=R_PASS,
                        user_agent="Making gifs of Jeff the plant for /r/"+subreddit+" by /u/"+MY_REDDIT_USER,
                        username=R_USER)
        Im = ImgurClient(I_CLID,I_SCRT,I_AXSS,I_REFR)
        try:
            makeDailyGif(R,Im)
        except Exception as e:
            print(e)
            R.redditor(MY_REDDIT_USER).message('gif failure','Error details:\n\n'+str(e))
        if int(time.strftime("%w",time.gmtime())) == 1:
            try:
                makeWeeklyGif(R,Im)
            except Exception as e:
                print(e)
                R.redditor(MY_REDDIT_USER).message('gif failure','Error details:\n\n'+str(e))
        if int(time.strftime("%d",time.gmtime())) == 1:
            try:
                makeMonthlyGif(R,Im)
            except Exception as e:
                print(e)
                R.redditor(MY_REDDIT_USER).message('gif failure','Error details:\n\n'+str(e))
