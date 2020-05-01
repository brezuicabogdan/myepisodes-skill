from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler, FallbackSkill
from mycroft.util.log import LOG
from mycroft.audio import wait_while_speaking
import feedparser
import hashlib
import datetime

__author__ = 'BreziCode'

MONTHS = {
    'Jan': "01",
    'Feb': "02",
    'Mar': "03",
    'Apr': "04",
    'May': "05",
    'Jun': "06",
    'Jul': "07",
    'Aug': "08",
    'Sep': "09",
    'Oct': "10",
    'Nov': "11",
    'Dec': "12"
}


class MyEpisodes(MycroftSkill):

    def __init__(self):
        super(MyEpisodes, self).__init__(name="MyEpisodes")
        self.unacquired = {}
        self.unwatched = {}
        self.shows = {}

    def initialize(self):
        if "useWatched" not in self.settings:
            self.settings["useWatched"] = False

    @intent_handler(IntentBuilder("query")
        .require("check")
        .require("episodes"))
    def handle_query_intent(self, message):
        if not self.isConfigured():
            return
        self.speak_dialog("querying")
        self.updateUnacquired()
        if self.settings.get("useWatched"):
            self.updateUnwatched()
        type = "unacquired"
        if self.unacquired['totalCnt'] == 0:
            self.speak_dialog('noNewEpisodes', data={'type': type})
            return
        if self.unacquired['airingTodayCnt'] > 0:
            self.speak_dialog('unacquiredEpisodesWithAiringToday', data={
                              'total': self.unacquired['totalCnt'], 'plural': 's' if self.unacquired['totalCnt'] > 1 else '', 'airingToday': self.unacquired['airingTodayCnt']})
        else:
            self.speak_dialog('unacquiredEpisodes', data={
                              'total': self.unacquired['totalCnt'], 'plural': 's' if self.unacquired['totalCnt'] > 1 else ''})
        self.speakEpisodesDetails(self.unacquired['episodes2speak'])
        wait_while_speaking()
        if self.settings.get("useWatched") and self.unwatched['totalCnt'] > 0:
            self.speak_dialog("unwatchedEpisodes", data={
                              'total': self.unwatched['totalCnt'], 'plural': 's' if self.unwatched['totalCnt'] > 1 else '', 'airingToday': self.unacquired['airingTodayCnt']})

    def stop(self):
        return True

    def speakEpisodesDetails(self, eps):
        if self.ask_yesno("details") == 'yes':
            self.speak(''.join(eps))
        else:
            self.speak_dialog('ok')

    def processFeed(self, feed):
        episodes = {}
        tmp_episodes = {}
        totalCnt = 0
        airingTodayCnt = 0
        if len(feed.entries) > 0 and 'guid' in feed.entries[0]:
            for entry in feed.entries:
                epMeta = {}
                if 'guid' not in entry:
                    self.log.error("Error parsing episode ")
                    self.log.error(entry)
                    break
                epGuidArr = entry.guid.split('-')
                if(len(epGuidArr) != 3):
                    self.log.error("Error parsing episode "+entry.guid)
                    continue
                showId = epGuidArr[0]
                season = int(epGuidArr[1])
                episode = int(epGuidArr[2])
                epMeta['episode'] = episode

                # episodeId = entry.guid
                epTitleArray = entry.title.split('][')
                if(len(epTitleArray) != 4):
                    self.log.error("Could not get show and episode titles")
                    continue
                else:
                    showName = epTitleArray[0].replace('[', '').strip()
                    if showName not in self.shows:
                        self.shows[showId] = showName
                    epMeta['epTitle'] = epTitleArray[2].strip()

                    airDate = epTitleArray[3].replace(
                        ']', '').strip().split('-')
                    airDate[1] = MONTHS[airDate[1]]
                    epMeta['epAirDate'] = '-'.join(airDate)
                    epMeta['epAirDate'] = datetime.datetime.strptime(
                        epMeta['epAirDate'], "%d-%m-%Y").date()
                    if epMeta['epAirDate'] == datetime.datetime.now().date():
                        airingTodayCnt = airingTodayCnt + 1
                        epMeta['airingToday'] = True
                    else:
                        epMeta['airingToday'] = False
                if showId not in episodes:
                    episodes[showId] = {}
                    tmp_episodes[showId] = {}
                if season not in episodes[showId]:
                    episodes[showId][season] = {}
                    tmp_episodes[showId][season] = []
                if episode not in episodes[showId][season]:
                    episodes[showId][season][episode] = epMeta
                    tmp_episodes[showId][season].append(episode)
                    totalCnt = totalCnt + 1
        else:
            self.log.debug('No episodes in feed')
            self.log.debug(feed)
        episodes2speak = []
        if totalCnt > 0:
            for showId in tmp_episodes:
                episodes2speak.append("%s " % self.shows[showId])
                for season in tmp_episodes[showId]:
                    episodes2speak.append("season %s, " % season)
                    season = tmp_episodes[showId][season]
                    season.sort()
                    startEp = season[0]
                    i = 1
                    endEp = startEp
                    seq = []
                    while i < len(season):
                        if season[i] == (endEp + 1):
                            endEp = season[i]
                        else:
                            seq.append(self._speakEpRange(startEp,endEp))
                            startEp = season[i]
                            endEp = startEp
                        i = i + 1
                    seq.append(self._speakEpRange(startEp,endEp))
                    if len(seq) == 1:
                        episodes2speak.append(seq[0])
                    else:
                        cnt = 0
                        for sq in seq:
                            if cnt > 0 :
                                if cnt < len(seq)-1:
                                    sq = ", %s" % sq
                                else:
                                    sq = " and %s " % sq
                            cnt = cnt + 1
                            episodes2speak.append(sq)
                    episodes2speak.append(', ')
        return {
            'episodes': episodes,
            'episodes2speak': episodes2speak,
            'totalCnt': totalCnt,
            'airingTodayCnt': airingTodayCnt,
            'updatedAt': datetime.datetime.now().date()
        }

    def _speakEpRange(self, minEp, maxEp):
        if minEp == maxEp:
            return "episode %s" % minEp
        elif maxEp == (minEp + 1):
            return "episodes %s and %s" % (minEp, maxEp)
        else:
            return "episodes %s through %s" % (minEp, maxEp)

    def updateUnacquired(self):
        self.log.debug("Updating unacquired episodes list")
        if not self.isConfigured():
            return False
        feed = self.getFeed("unacquired")
        if feed:
            self.log.debug("Got %s items from unacquired feed" %
                           (len(feed.entries)))
            self.unacquired = self.processFeed(feed)

    def updateUnwatched(self):
        self.log.debug("Updating unwatched episodes list")
        if not self.isConfigured():
            return False
        feed = self.getFeed("unwatched")
        if feed:
            self.log.debug("Got %s items from unwatched feed" %
                           (len(feed.entries)))
            self.unwatched = self.processFeed(feed)

    def getFeed(self, type):
        self.log.debug("Requesting feed")
        if not self.isConfigured():
            return False
        user = self.settings.get("username")
        pwHash = hashlib.md5(self.settings.get(
            "password").encode()).hexdigest()
        feedURL = "http://www.myepisodes.com/rss.php?feed=" + \
            type+"&uid=" + user+"&pwdmd5="+pwHash+"&showignored=0"
        self.log.debug("Using feed URL: %s" % (feedURL))
        feed = feedparser.parse(feedURL)
        if feed.status is not 200:
            self.log.error(
                "Error getting RSS feed. Reply HTTP code: " % (feed.status))
            self.speak_dialog('errorHTTPCode')
        elif feed.bozo:
            self.log.error("Error parsing RSS feed.")
            if hasattr(feed, 'bozo_exception'):
                self.log.exception(feed.bozo_exception) 
            self.speak_dialog('errorParseFeed')
        else:
            return feed

    def isConfigured(self):
        if 'username' not in self.settings or 'password'not in self.settings:
            self.log.error("Skill not configured")
            self.speak_dialog("notSetUp")
            return False
        return True
        
def create_skill():
    return MyEpisodes()
