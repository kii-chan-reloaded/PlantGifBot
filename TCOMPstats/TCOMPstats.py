#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  TCOMPstats.py
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

"""
TCOMPstats, TakeCareOfMyPlant stats.
Not the most elegant of code, but it does it's job.
Set up for use on the first day of the month. Will roll through
/u/takecareofmyplant's post history and pick out all of the posts from
the previous month, then saves it along with the votes of everyone who 
replied to at least one of them. The bot will create a graph with voting
trends for the past month, then PM each person who contributed with some
simple statistics about their voting history. 
"""

import praw
import re
from PIL import Image,ImageDraw
import time
import TCOMPstatsSecret
import math
from imgurpython import ImgurClient

def getCommentScore(comment):
    # Taken directly from /u/takecareofmyyplant's source code
    yes = re.search(r'\byes\b', comment.body, re.IGNORECASE) or re.search(r'\baye\b', comment.body, re.IGNORECASE)
    no = re.search(r'\bno\b', comment.body, re.IGNORECASE) or re.search(r'\bnot on your nelly\b', comment.body, re.IGNORECASE)
    if yes and no:
        return 0
    elif yes: 
        return 1
    elif no:
        return -1
    else:
        return 0

def getWateringResult(submission):
    global subStats
    # Recycled from /u/PlantGifBot's source code
    match = re.search(r"Yes \| No\n---\|--\n([0-9]+) \| ([0-9]+)",submission.selftext)
    yes = int(match.group(1))
    no = int(match.group(2))
    date = int(re.search("Today is .*, .* ([0-9]+)",submission.title).group(1))
    subStats[date] = {'yes':yes,'no':no}
    if yes > no:
        return 1
    else:
        return -1

def gatherData(R):
    # Runs at the start of the month, give ourselves 2 days of wiggle room
    lastMonth = time.time()-2*24*60*60
    redditors = {}
    for post in R.redditor('takecareofmyplant').submissions.new(limit=None):
        # If post is over 32 days old, quit
        if post.created_utc <= lastMonth-30*24*60*60:
            return redditors
        # If the post is an announcement or something, skip it by checking
        # if the full name of the month was in the post title or not 
        if time.strftime("%B",time.gmtime(lastMonth)) not in post.title:
            continue
        try:
            dayResult = getWateringResult(post)
        except AttributeError:
            # Likely today's post
            continue
        # Get all the root comments
        post.comments.replace_more(limit = None, threshold = 0)
        for c in post.comments.list():
            try:
                user = c.author.name
            except:
                # Probably a deleted account
                continue
            try:
                redditors[user].append( {'vote':getCommentScore(c),'result':dayResult} )
            except KeyError:
                redditors[user] = [ {'vote':getCommentScore(c),'result':dayResult} ]

def analyze(user):
    total = len(user)
    ys = 0
    ns = 0
    agreement = 0
    waterings = 0
    for data in user:
        if data['vote'] == 1:
            ys += 1
        elif data['vote'] == -1:
            ns += 1
        if data['vote'] == data['result']:
            agreement += 1
            if data['vote'] == 1:
                waterings += 1
    return {'yes':ys,'no':ns,'agree':agreement,'water':waterings,'total':total}
    
def subStatistics(subStats,data):
    ######
    # This is pretty janky, but I'm too lazy to learn new things like ImageFont or numpy or whatever
    # ... It works, okay? What more do you want from me?
    ######
    
    # Some numbers
    comp = [ subStats[day]['yes']+subStats[day]['no'] for day in subStats ]
    totalVotes = sum(comp)
    mostVotes = max(comp)
    totalVotesY = sum( [ subStats[day]['yes'] for day in subStats ] )
    totalVotesN = sum( [ subStats[day]['no'] for day in subStats ] )
    uniqueVoters = len(data)
    # Make image
    I = Image.new("RGB",(1000,600))
    I.paste((255,255,255),(0,0,1000,600))
    D = ImageDraw.Draw(I)
    header = "/r/TakeCareOfMyPlant "+time.strftime("%B",time.gmtime(time.time()-2*24*60*60))+" Voting Stats"
    # Center and resize header
    sizing = D.textsize(header)
    D.text((500-int(sizing[0]/2),20),header,(0,0,0))
    C = I.crop((500-int(sizing[0]/2),20,500+math.ceil(sizing[0]/2),20+sizing[1]))
    C = C.resize((C.size[0]*3,C.size[1]*3))
    I.paste(C,(500-int(C.size[0]/2),20,500+math.ceil(C.size[0]/2),20+C.size[1]))
    # define line colors
    gridC = (128,128,128)
    totalC = (50,175,100)
    yesC = (50,100,255)
    noC = (255,50,100)
    # Make graph
    for thickness in range(3):
        D.rectangle((100+thickness,40+C.size[1]+thickness,950-thickness,390+C.size[1]-thickness),None,(0,0,0))
    for i in range(10):
        D.text((80,40+C.size[1]+int(350/10*i)),str(int(mostVotes-mostVotes/10*i)),(0,0,0))
        D.line((100,40+C.size[1]+int(350/10*i),950,40+C.size[1]+int(350/10*i)),gridC)
    daysInMonth = [day for day in range(32) if time.strftime("%B",time.gmtime(time.time()-day*24*60*60)) == time.strftime("%B",time.gmtime(time.time()-2*24*60*60))]
    previousDay = None
    for day in daysInMonth:
        actualDay = time.strftime("%d",time.gmtime(time.time()-day*24*60*60))
        X = 950-int(day/len(daysInMonth)*850)
        Y = 390+C.size[1]
        D.text((X,400+C.size[1]),actualDay,(0,0,0))
        D.line((X,Y-350,X,Y),gridC)
        try:
            thisDay = subStats[int(actualDay)]
        except:
            previousDay = None
            continue
        if not previousDay:
            previousDay = thisDay
            continue
        D.line((X,Y-350*(thisDay['yes']+thisDay['no'])/mostVotes,X+int(1/len(daysInMonth)*850),Y-350*(previousDay['yes']+previousDay['no'])/mostVotes),totalC,width=3)
        D.line((X,Y-350*thisDay['yes']/mostVotes,X+int(1/len(daysInMonth)*850),Y-350*previousDay['yes']/mostVotes),yesC,width=3)
        D.line((X,Y-350*thisDay['no']/mostVotes,X+int(1/len(daysInMonth)*850),Y-350*previousDay['no']/mostVotes),noC,width=3)
        previousDay = thisDay
    # Make legend
    D.text((20,160+C.size[1]),"yes",yesC)
    D.text((20,180+C.size[1]),"no",noC)
    D.text((20,200+C.size[1]),"total",totalC)
    # Extra stuff
    extra = format("total votes: {0}".format(totalVotes),"20")+" | total 'yes': {0}\n".format(totalVotesY)+format("unique voters: {0}".format(uniqueVoters),"20")+" | total 'no': {0}".format(totalVotesN)
    sizing = D.multiline_textsize(extra)
    D.text((500-int(sizing[0]/2),425+C.size[1]),extra,(0,0,0))
    E = I.crop((500-int(sizing[0]/2),425+C.size[1],500+math.ceil(sizing[0]/2),425+C.size[1]+sizing[1]))
    E = E.resize((E.size[0]*2,E.size[1]*2))
    I.paste(E,(500-int(E.size[0]/2),425+C.size[1],500+math.ceil(E.size[0]/2),425+C.size[1]+E.size[1]))
    # Save and return filepath
    fn = "/home/keaton/Pictures/TCOMPstats"+time.strftime("%B",time.gmtime(time.time()-2*24*60*60))+".png"
    I.save(fn)
    return fn

subStats = {}

if __name__ == '__main__':
    R = praw.Reddit(client_id = TCOMPstatsSecret.clientID,
                    client_secret = TCOMPstatsSecret.secret,
                    password = TCOMPstatsSecret.password,
                    user_agent = "Making monthly statistics for /r/TakeCareOfMyPlant by /u/Omnipotence_is_bliss",
                    username = TCOMPstatsSecret.username)
    ###########
    # For ease of switching back and forth in testing, also can save a ton of time.
    ###########
    data = gatherData(R)
    with open("/home/keaton/TCOMPstatstest.data","w") as out:
        out.write(str(data))
    with open("/home/keaton/TCOMPstatstest.subdata","w") as out:
        out.write(str(subStats))
    ###########
    #with open("/home/keaton/TCOMPstatstest.data","r") as out:
    #    data = eval(out.read())
    #with open("/home/keaton/TCOMPstatstest.subdata","r") as out:
    #    subStats = eval(out.read())
    ###########
    
    # Flag users who didn't vote, analyze and make reply to users who did
    for user in data:
        stats = analyze(data[user])
        # More aggressive filtering, saves time & bandwidth, but who cares.
        #if (stats['yes'] == 0 and stats['no'] == 0) or stats['total'] == 1:
        if stats['yes'] == 0 and stats['no'] == 0:
            data[user]=None
            continue
        reply = """Hello, /u/{0}!
        
        Within the past month, you participated in watering Jeff the plant
        over at /r/TakeCareOfMyPlant. [The subreddit-wide voting data can 
        be viewed here](REDDITLINK). Here is some fun data I've compiled
        about your own voting records:
        
        * You voted `yes` a total of {1} time(s), accounting for {2}% of your votes
        * You voted `no` a total of {3} time(s), accounting for {4}% of your votes
        * {5}% of your votes aligned with the watering result
        * You were directly responsible for watering Jeff {6} time(s)
        
        Jeff looks forward to receiving your next vote!
        """.format(user,stats['yes'],int(stats['yes']/stats['total']*100),
                   stats['no'],int(stats['no']/stats['total']*100),
                   int(stats['agree']/stats['total']*100),stats['water']).replace("\n        \n        ","\n\n").replace("\n        *","\n*").replace("\n        "," ")
        # Done using individual data, so replace it with the reply for ease later
        data[user]= reply
    # Remove flagged users
    data = { user:data[user] for user in data if data[user] }
    # Create the graph and return the filepath it saved to
    filepath = subStatistics(subStats,data)
    # Upload to Imgur
    Im = ImgurClient(TCOMPstatsSecret.ImClid,TCOMPstatsSecret.ImScrt,TCOMPstatsSecret.ImAxss,TCOMPstatsSecret.ImRefr)
    config = {"title":"Monthly Voting Data for "+time.strftime("%B",time.gmtime(time.time()-2*24*60*60))}
    t=0
    while t<30:
        try:
            uploaded = Im.upload_from_path(filepath,config=config,anon=False)
            break
        except:
            uploaded = False
            t+=1
            time.sleep(2)
    if uploaded:
        # Slap it on reddit
        rPost = R.subreddit("takecareofmyplant").submit("Monthly Voting Data for "+time.strftime("%B",time.gmtime(time.time()-2*24*60*60)),url=uploaded['link'])
        # Not necessary outside of testing
        #R.redditor("Omnipotence_is_bliss").message("Monthly stats uploaded",uploaded['link'])
        # Start notifying individuals about their previous month
        # TAKES FOREVEEERRRRRRRR
        for user in data:
            # Again, testing
            #if user != "Omnipotence_is_bliss":
            #    continue
            t = 0
            while t < 10:
                try:
                    R.redditor(user).message("Your /r/TakeCareOfMyPlant monthly voting statistics",data[user].replace("REDDITLINK",rPost.shortlink))
                    # Overkill
                    t=400
                except:
                    t+=1
