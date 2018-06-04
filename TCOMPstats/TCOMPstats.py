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
from PIL import Image,ImageDraw,ImageFont
import time
import pickle
import TCOMPstatsSecret
from imgurpython import ImgurClient

myPath = re.search(r".*?([/\\].*)",__file__[::-1]).group(1)[::-1]
from os.path import join
if join("home","pi") in myPath:
    home = "/home/pi/"
elif join("home","keaton") in myPath:
    home = "/home/keaton/"

def getCommentScore(comment):
    # Taken mostly directly from /u/takecareofmyplant's source code
    yes = re.search(r'\byes\b', comment.body, re.IGNORECASE) or re.search(r'\baye\b', comment.body, re.IGNORECASE) or re.search(r'\bprost\b', comment.body, re.IGNORECASE)
    no = re.search(r'\bno\b', comment.body, re.IGNORECASE) or re.search(r'\bnot on your nelly\b', comment.body, re.IGNORECASE) or re.search(r'\bnein\b', comment.body, re.IGNORECASE)
    if yes and no:
        raise Exception
    elif yes:
        return 1
    elif no:
        return -1
    else:
        raise Exception

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
    lastMonth = time.gmtime()[1]-1
    redditors = {}
    for post in R.redditor('takecareofmyplant').submissions.new(limit=None):
        # If post is over 32 days old, quit
        if time.gmtime(post.created_utc)[1] < lastMonth:
            return redditors
        # Skip announcement posts and posts from this month- we'll pick those up next month
        if (time.strftime("%B",time.gmtime(time.time()-7*24*60*60)) not in post.title) or (time.strftime("%B") in post.title):
            print("Skipped "+post.title)
            continue
        try:
            dayResult = getWateringResult(post)
        except AttributeError:
            # Today's post? This shouldn't happen but just in case
            continue
        # Pick out the date
        date = eval(time.strftime("%Y%m%d",time.gmtime(post.created_utc)))
        # Get all the root comments
        post.comments.replace_more(limit = None, threshold = 0)
        for c in post.comments:
            try:
                user = c.author.name
            except:
                # Probably a deleted account
                continue
            if user == "takecareofmyplant":
                continue
            try:
                if user in redditors.keys():
                    if date not in [ item['date'] for item in redditors[user] ]:
                        redditors[user].append( {'date':date,'vote':getCommentScore(c),'result':dayResult} )
                else:
                    redditors[user] = [ {'date':date,'vote':getCommentScore(c),'result':dayResult} ]
            except:
                continue
    return redditors

def analyze(user):
    total = len(user)
    ys = 0
    ns = 0
    agreement = 0
    waterings = 0
    longStreak = 0
    currStreak = 1
    user = sorted(user,key=lambda date:date['date'])
    for i,data in enumerate(user):
        # Voting stuff
        if data['vote'] == 1:
            ys += 1
        elif data['vote'] == -1:
            ns += 1
        if data['vote'] == data['result']:
            agreement += 1
            if data['vote'] == 1:
                waterings += 1
        # Streak stuff
        if data['date'] == user[i-1]['date'] +1:
            currStreak += 1
        elif data['date'] == user[i-1]['date']:
            pass
        else:
            if currStreak > longStreak:
                longStreak = currStreak
            currStreak = 1
    # Make sure longest streak is recorded
    if currStreak > longStreak:
        longStreak = currStreak

    return {'yes':ys,'no':ns,'agree':agreement,'water':waterings,'total':total,'streak':longStreak}
    
def columnize(L,D,f,drawColor):
    """
    Make the most efficient table possible
    """
    L = sorted(L)
    # Figure out the width/height of one character
    charW = D.textsize("0",font=f)[0]
    charH = int(D.textsize("y\n0",font=f)[1]/2)
    # Max of string lists seems wonky. Working around it
    lenList = [len(u) for u in L]
    big = len(L[lenList.index(max(lenList))])+1
    # Determine the biggest grid we can make
    columns = int(425/((big)*charW))
    rowsMax = int(100/charH)
    rows = int(len(L)/columns) if len(L)%columns == 0 else int(len(L)/columns)+1
    # If it's not big enough, reduce font size and try again
    if rows > rowsMax:
        columnize(L,D,f.font_variant(size=f.size-1),drawColor)
        return None
    # Make the table and write it
    out = ""
    for r in range(rows):
        for c in range(columns):
            if r*columns+c < len(L):
                out += format(L[r*columns+c],str(big))
                if c == columns -1:
                    out += "\n"
    D.text((575,500),out,fill=drawColor,font=f)
    # Add lines between columns for readability
    for c in range(columns-1):
        D.line((575+((c+1)*2*big-1)/2*charW,500,575+((c+1)*2*big-1)/2*charW,500+rows*charH),fill=drawColor)

def subStatistics(subStats,data,longestStreak):
    """
    BLOODY AND UGLY BUT IT TURNS OUT OKAY
    """
    # Some numbers
    comp = [ subStats[day]['yes']+subStats[day]['no'] for day in subStats ]
    totalVotes = sum(comp)
    mostVotes = max(comp)
    totalVotesY = sum( [ subStats[day]['yes'] for day in subStats ] )
    totalVotesN = sum( [ subStats[day]['no'] for day in subStats ] )
    uniqueVoters = len(data)
    # Define colors
    bkg = (255,255,255,255)
    # Set the grid color to inverse of the background at full opacity
    drawColor = tuple(255-n for n in bkg[:-1]).__add__((255,))
    # yes/no/total colors are used with `.__add__((A,))` where A is alpha
    yesColor = (50,100,255)
    noColor = (255,50,100)
    totalColor = (50,175,100)
    # Define fonts
    titleFont = ImageFont.truetype(join(home,".fonts/UbuntuMono-R.ttf"),36)
    subFont = titleFont.font_variant(size=24)
    legendFont = titleFont.font_variant(size=12)
    # Make Image
    I = Image.new("RGBA",(1000,600),bkg)
    D = ImageDraw.Draw(I)
    header = "/r/TakeCareOfMyPlant "+time.strftime("%B %Y",time.gmtime(time.time()-2*24*60*60))+" Voting Stats"
    sizing = D.textsize(header,font=titleFont)
    D.text((500-int(sizing[0]/2),14),header,fill=drawColor,font=titleFont)
    # Make graph
    G = Image.new("RGBA",(900,372),bkg)
    GD = ImageDraw.Draw(G)
    # To make the graph correctly be transparent, gotta do some finessing
    Temp = Image.new("RGBA",(850,350),bkg)
    TMask = Image.new("L",(850,350),"white")
    TD = ImageDraw.Draw(TMask)
    for i in range(10):
        # Draw the text on the graph layer, graw the grid on the mask
        GD.text((0,int(350/10*i)),format(str(int(mostVotes-mostVotes/10*i))[::-1],"3")[::-1],(0,0,0,255),font=legendFont)
        TD.line((0,int(350/10*i),850,int(350/10*i)),0)
    GD.text((0,345),'  0',drawColor,font=legendFont)
    # Easily manage different graph datas
    graphParts = {}
    for part in ["yes","no","total"]:
        graphParts[part] = {}
        # coordinates for the polygon/line
        graphParts[part]["poly"] = [(850,350)]
        # layer mask
        graphParts[part]["M"] = Image.new("L",(850,350),"white")
        # line color
        graphParts[part]["outline"] = eval(part+"Color.__add__((255,))")
        # polygon fill
        if part == "total":
            graphParts[part]["fill"] = None
        else:
            graphParts[part]["fill"] = eval(part+"Color.__add__((128,))")
    # Get how many days ago each day in the last month was
    daysInMonth = [day for day in range(32) if time.strftime("%B",time.gmtime(time.time()-day*24*60*60)) == time.strftime("%B",time.gmtime(time.time()-2*24*60*60))]
    for day in daysInMonth:
        # Get the date for each day
        actualDay = time.strftime("%d",time.gmtime(time.time()-day*24*60*60))
        # X position for this day according to the graph, add 20 for the graph layer position
        X = 850-int((day-1)/(len(daysInMonth)-1)*850)
        GD.text((X+20,360),actualDay,drawColor,font=legendFont)
        TD.line((X,0,X,350),0)
        try:
            # If voting data exists for this day, use it
            thisDay = subStats[int(actualDay)]
        except:
            # Otherwise, cut the graph off and continue on the next day
            for part in graphParts:
                if day != daysInMonth[0]:
                    graphParts[part]["poly"].append((850-int((day-2)/(len(daysInMonth)-1)*850),350))
                graphParts[part]["poly"].append((X,350))
                if day != daysInMonth[-1]:
                    graphParts[part]["poly"].append((850-int((day)/(len(daysInMonth)-1)*850),350))
            continue
        # Add coordinates for the day to the polygon
        graphParts["yes"]["poly"].append((X,350*(1-thisDay["yes"]/mostVotes)))
        graphParts["no"]["poly"].append((X,350*(1-thisDay["no"]/mostVotes)))
        graphParts["total"]["poly"].append((X,350*(1-(thisDay["yes"]+thisDay["no"])/mostVotes)))
    # Add grid to graph
    Temp = Image.composite(Temp,Image.new("RGBA",(850,350),drawColor),TMask)
    for part in graphParts:
        # complete the polygon
        graphParts[part]["poly"].append((0,350))
        # Initiate drawing
        PD = ImageDraw.Draw(graphParts[part]["M"])
        try:
            PD.polygon(graphParts[part]["poly"],fill=255-graphParts[part]["fill"][3])
        except:
            PD.polygon(graphParts[part]["poly"],fill=graphParts[part]["fill"])
        # Outline the polygon and apply the mask
        PD.line(graphParts[part]["poly"],width=3,fill=255-graphParts[part]["outline"][3])
        Temp = Image.composite(Temp,Image.new("RGBA",(850,350),graphParts[part]["outline"]),graphParts[part]["M"])
    # Put the corrected graph transparency on the graph layer
    G.paste(Temp,(20,0),mask=Temp)
    # Make a frame around the graph
    for thickness in range(3):
        GD.rectangle((20+thickness,0+thickness,870-thickness,350-thickness),None,drawColor)
    # Paste it to full image and add legend
    I.paste(G,(80,70))
    D.text((20,220),"yes",yesColor.__add__((255,)),font=subFont)
    D.text((20,260),"no",noColor.__add__((255,)),font=subFont)
    D.text((20,300),"total",totalColor.__add__((255,)),font=subFont)
    # Make pie chart of yes vs no votes
    D.pieslice((10,460,110,560),-90,360*totalVotesY/totalVotes-90,fill=yesColor.__add__((255,)))
    D.pieslice((10,460,110,560),270-360*totalVotesN/totalVotes,270,fill=noColor.__add__((255,)))
    D.text((115,470),format("Total 'yes':","13")+format(str(totalVotesY)[::-1],"5")[::-1],fill=yesColor.__add__((255,)),font=subFont)
    D.text((115,500),format("Total 'no':","13")+format(str(totalVotesN)[::-1],"5")[::-1],fill=noColor.__add__((255,)),font=subFont)
    D.text((115,530),format("Total votes:","13")+format(str(totalVotes)[::-1],"5")[::-1],fill=totalColor.__add__((255,)),font=subFont)
    # More stats
    D.text((350,470),"Unique voters: "+str(uniqueVoters),fill=drawColor,font=subFont)
    D.text((350,500),"Longest streak: "+str(longestStreak),fill=drawColor,font=subFont)
    # Showcase the super-outstanding gardeners
    D.text((620,470),"Longest streak voters:",fill=drawColor,font=subFont)
    outstandingGardeners = [user for user in data if data[user]['stats']['streak'] == longestStreak]
    columnize(outstandingGardeners,D,legendFont,drawColor)
    #I.show() # testing purposes
    # Save and return filepath
    fn = join(myPath,time.strftime("%B %Y.png",time.gmtime(time.time()-2*24*60*60)))
    I.save(fn)
    return fn


subStats = {}
with open(join(myPath,"voter_archive.pickle"),"rb") as f:
    voterArchive = pickle.load(f)

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
    #with open(myPath+"TCOMPstatstest.data","w") as out:
    #    out.write(str(data))
    #with open(myPath+"TCOMPstatstest.subdata","w") as out:
    #    out.write(str(subStats))
    ###########
    #with open(myPath+"TCOMPstatstest.data","r") as out:
    #    data = eval(out.read())
    #with open(myPath+"TCOMPstatstest.subdata","r") as out:
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
        if user in voterArchive.keys():
            for thing in ['total','yes','no','agree','water']:
                voterArchive[user][thing] = voterArchive[user][thing] + stats[thing]
        else:
            voterArchive[user] = {}
            for thing in ['total','yes','no','agree','water']:
                voterArchive[user][thing] = stats[thing]
        reply = """Hello, /u/{0}!
        
        Within the past month, you participated in watering Jeff the plant
        over at /r/TakeCareOfMyPlant. [The subreddit-wide voting data can 
        be viewed here](REDDITLINK). Here is some fun data I've compiled
        about your own voting records:
        
        * You voted `yes` a total of {1} time(s), accounting for {2}% of your votes
        * You voted `no` a total of {3} time(s), accounting for {4}% of your votes
        * {5}% of your votes aligned with the watering result
        * You were directly responsible for watering Jeff {6} time(s)
        * Your longest voting streak this month was {7} day(s)
        
        With this data, here are your updated lifetime voting statistics:
        
        * You have voted {8} times!
         * `Yes`: {9}
         * `No`: {10}
        * {11}% of your votes aligned with the watering results
        * You have been directly responsible for watering Jeff {12} time(s)!
        
        Jeff looks forward to receiving your next vote!
        """.format(user, stats['yes'], int(stats['yes']/stats['total']*100),
                   stats['no'], int(stats['no']/stats['total']*100),
                   int(stats['agree']/stats['total']*100), stats['water'],
                   stats['streak'], voterArchive[user]['total'],
                   voterArchive[user]['yes'], voterArchive[user]['no'],
                   int(voterArchive[user]['agree']/voterArchive[user]['total']*100),
                   voterArchive[user]['water']).replace("\n        \n        ","\n\n").replace("\n         *","\n *").replace("\n        *","\n*").replace("\n        "," ")
        # Done using individual data, so replace it with the reply and stats
        data[user]= {'reply':reply,'stats':stats,'archive':voterArchive[user]}
    # Remove flagged users
    data = { user:data[user] for user in data if data[user] }
    # Grab lifetime numbers to put in the comment section
    voteSum = 0
    mostVotes = max( [voterArchive[user]['total'] for user in voterArchive] )
    mostYes = max( [voterArchive[user]['yes'] for user in voterArchive] )
    mostNo = max( [voterArchive[user]['no'] for user in voterArchive] )
    mostWater = max( [voterArchive[user]['water'] for user in voterArchive] )
    aligns = [int(voterArchive[user]['agree']/voterArchive[user]['total']*100) for user in voterArchive if voterArchive[user]['total'] > 10]
    mostAligned = max(aligns)
    leastAligned = min(aligns)
    mostVoters = []
    mostYesers = []
    mostNoers = []
    mostWaters = []
    mostAligners = []
    leastAligners = []
    for user in voterArchive:
        voteSum += voterArchive[user]['total']
        if voterArchive[user]['total'] == mostVotes:
            mostVoters.append(user)
        if voterArchive[user]['yes'] == mostYes:
            mostYesers.append(user)
        if voterArchive[user]['no'] == mostNo:
            mostNoers.append(user)
        if voterArchive[user]['water'] == mostWater:
            mostWaters.append(user)
        if int(voterArchive[user]['agree']/voterArchive[user]['total']*100) == mostAligned and voterArchive[user]['total'] > 10:
            mostAligners.append(user)
        if int(voterArchive[user]['agree']/voterArchive[user]['total']*100) == leastAligned and voterArchive[user]['total'] > 10:
            leastAligners.append(user)
    longestStreak = max([ data[user]['stats']['streak'] for user in data ])
    # Create the graph and return the filepath it saved to
    filepath = subStatistics(subStats,data,longestStreak)
    input("Proceed to upload?")
    # Upload to Imgur
    Im = ImgurClient(TCOMPstatsSecret.ImClid,TCOMPstatsSecret.ImScrt,TCOMPstatsSecret.ImAxss,TCOMPstatsSecret.ImRefr)
    config = {"title":"(Corrected) Monthly Voting Data for "+time.strftime("%B %Y",time.gmtime(time.time()-2*24*60*60))}
    t=0
    while t<30:
        try:
            uploaded = Im.upload_from_path(filepath,config=config,anon=False)
            # overkill
            t=400
        except:
            uploaded = False
            t+=1
            time.sleep(2)
    if uploaded:
        # Slap it on reddit
        rPost = R.subreddit("takecareofmyplant").submit("Monthly Voting Data for "+time.strftime("%B %Y",time.gmtime(time.time()-2*24*60*60)),url=uploaded['link'])
        rPost.reply("""#/r/TakeCareOfMyPlant Hall of Fame Monthly Update\n\nJeff has received {0} votes from {18} unique voters as of yesterday's voting.\n\n
                    The redditor{1} with the highest contribution{2} of lifetime votes {4} {5} ({3})\n\n
                    {6} has the record for most `yes` votes ({7})\n\n
                    {8} has the record for most `no` votes ({9})\n\n
                    {10} has the record for most waterings ({11})\n\n
                    {12} users have the record for highest vote-to-outcome alignment among voters with more than 10 votes ({13}%){14}\n\n
                    {15} users have the record for lowest vote-to-outcome alignment among voters with more than 10 votes ({16}%){17}""".format(
                    voteSum,
                    "s" if len(mostVoters) >1 else "",
                    "s" if len(mostVoters) >1 else "",
                    mostVotes,
                    "are" if len(mostVoters) >1 else "is",
                    ", ".join(["/u/"+user for user in mostVoters]),
                    ", ".join(["/u/"+user for user in mostYesers]),
                    mostYes,
                    ", ".join(["/u/"+user for user in mostNoers]),
                    mostNo,
                    ", ".join(["/u/"+user for user in mostWaters]),
                    mostWater,
                    str(len(mostAligners)),
                    mostAligned,
                    ". Users in this group who voted last month are: "+", ".join(["/u/"+user for user in mostAligners if user in data]) if ["/u/"+user for user in mostAligners if user in data] else ". None of them voted last month",
                    str(len(leastAligners)),
                    leastAligned,
                    ". Users in this group who voted last month are: "+", ".join(["/u/"+user for user in leastAligners if user in data]) if ["/u/"+user for user in leastAligners if user in data] else ". None of them voted last month",
                    str(len(voterArchive))).replace("                    ",""))
        # Not necessary outside of testing
        #R.redditor("Omnipotence_is_bliss").message("Monthly stats uploaded",uploaded['link'])
        #########
        # Start notifying individuals about their previous month
        # TAKES FOREVEEERRRRRRRR
        for user in data:
            # Again, testing
            #if user != "Omnipotence_is_bliss":
            #    continue
            if data[user]['stats']['streak'] == longestStreak:
                data[user]['reply'] = data[user]['reply'].replace("day(s)","days(s)\n * You were tied for the longest streak this month!")
            t = 0
            while t < 10:
                try:
                    R.redditor(user).message("Your /r/TakeCareOfMyPlant monthly voting statistics",data[user]['reply'].replace("REDDITLINK",rPost.shortlink))
                    # Overkill
                    t=400
                except:
                    t+=1
    else:
        R.redditor("Omnipotence_is_bliss").message("Failure to upload","The monthly stat graph failed to upload")
        for user in data:
            # Again, testing
            #if user != "Omnipotence_is_bliss":
            #    continue
            if data[user]['stats']['streak'] == longestStreak:
                data[user]['reply'] = data[user]['reply'].replace("day(s)","days(s)\n * You were tied for the longest streak this month!")
            t = 0
            while t < 10:
                try:
                    R.redditor(user).message("Your /r/TakeCareOfMyPlant monthly voting statistics",data[user]['reply'].replace("[The subreddit-wide voting data can be viewed here](REDDITLINK). ","The subreddit-wide voting data should be uploaded sometime today. "))
                    # Overkill
                    t=400
                except:
                    t+=1

with open(join(myPath,"voter_archive.pickle"),"wb") as f:
    pickle.dump(voterArchive,f)
