import praw
import re
import time
import pickle
import TCOMPstatsSecret

def getCommentScore(comment):
    # Taken mostly directly from /u/takecareofmyyplant's source code
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
    # Recycled from /u/PlantGifBot's source code
    match = re.search(r"Yes \| No\n---\|--\n([0-9]+) \| ([0-9]+)",submission.selftext)
    yes = int(match.group(1))
    no = int(match.group(2))
    if yes > no:
        return 1
    else:
        return -1

def gatherData(R):
    redditors = {}
    
    #Get GMT for the start of this month
    now=time.gmtime()
    
    #for post in R.redditor('takecareofmyplant').submissions.new(limit=30):
    for post in R.redditor('takecareofmyplant').submissions.new(limit=None):
        # Skip announcement posts and posts from this month- we'll pick those up next month
        ptime = time.gmtime(post.created_utc)
        if (time.strftime("%B",ptime) not in post.title) or (now[0]==ptime[0] and now[1]==ptime[1]):
            print("Skipped "+post.title)
            continue
        try:
            dayResult = getWateringResult(post)
        except AttributeError:
            # Today's post? This shouldn't happen but just in case
            continue
        print('Getting data for post:',post.title)
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

voterArchive = {}

if __name__ == '__main__':
    R = praw.Reddit(client_id = TCOMPstatsSecret.clientID,
                    client_secret = TCOMPstatsSecret.secret,
                    password = TCOMPstatsSecret.password,
                    user_agent = "Making monthly statistics for /r/TakeCareOfMyPlant by /u/Omnipotence_is_bliss",
                    username = TCOMPstatsSecret.username)
    data = gatherData(R)
    print("{} users found in data. Starting analysis".format(len(data)))
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

with open("/home/keaton/bots/TCOMPstats/voter_archive.pickle","wb") as f:
    pickle.dump(voterArchive,f)
