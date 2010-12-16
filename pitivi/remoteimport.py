from urllib2 import Request, urlopen, URLError
from httplib import HTTPException
from urlparse import urlparse
from socket import error
from urllib import urlcleanup, urlretrieve, unquote
import time
import os
import gio
import gtk
import threading
import HTMLParser
from pitivi.signalinterface import Signallable
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs

std_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.11) Gecko/20101019 Firefox/3.6.11',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
}

class BlipIE:

    def process(self,template, page = 1):
        request = Request(template, None, std_headers)
        try:
            video_info_webpage = urlopen(request).read()
            if video_info_webpage is not None:
                video_info = parse_qs(video_info_webpage)
                return video_info
            else:
                return None
        except (URLError, HTTPException, error), err:
            return None

    def getVideoUrl(self, filename):
        feed = self.process("".join('http://blip.tv' + filename))
        if feed is None:
            return
        for element in feed:
            if 'Select a format' in element:
                videoUrl = feed[element][0].split('?filename=')
                if '">Source' in videoUrl[1]:
                    videoUrl = videoUrl[1].split('">Source')[0]
                    return videoUrl
                elif '">source ' in videoUrl[1]:
                    videoUrl = videoUrl[1].split('">source')[0]
                    return videoUrl

    def search(self, query, page = 1):
        bigList = []
        template = "".join('http://blip.tv/search?q=' + query + '&page=' + str(page))
        print template
        a = self.process(template)
        if a == None :
            return
        for e in a:
            if '<div class' in e:
                for i in a[e]:
                    if '<a href="' in i:
                        part = i[i.index('<a href="') + 9:]
                        if ('">') in part:
                            littleList = part[: part.index('">')]
                            littleList = littleList.split('" title="Watch ')
                        else:
                            break
                        if '<img class="thumb" src="' in i:
                            part = i[i.index('<img class="thumb" src="'):]
                            thumburl = part[24:part.index('" width')]
                            littleList.append(thumburl)
                        else :
                            break
                        if '<span class="EpisodeDuration">'in i:
                            part = i[i.index('<span class="EpisodeDuration">'):]
                            duration = part[30 : part.index('</span>')]
                            littleList.append(duration)
                        bigList.append(littleList)
                return bigList

class WebArchiveIE(Signallable):
    __signals__ = {
        'info retrieved' : ['info'],
        }

    def main(self, query, page = 1):
        print page
        self.thumblist = []
        self.namelist = []
        self.feedlist = []
        self.linklist = []
        self.count = 0
        self.previous_video = None
        urlcleanup()

        feed = self.process(query, page)
        self.videoList = []
        timestart = time.time()
        if feed is not None :
            return feed

    def specThumb(self, element):
        count = 0
        namelist = []
        thumblist = []
        for e in element:
            if "thumbCell" in e:
                count +=1
                self.downloadFeed = e
                downloadFeed = e
                self.feedlist.append(downloadFeed)
                thumburl = self._getThumbUrl(downloadFeed)
                thumblist.append(thumburl)
        return  thumblist

    def getLinks(self, feed):
        self.linklist = []
        video = self._getSpecificVideo(feed)

        p = linkParser()
        try :
            p.feed(video[0])
            links = []
            for link in p.links:
                links.append(link)
            self.linklist.append(links)
        except :
            return None
        return self.linklist

    def _getThumbs(self, feed):
        try :
            start = feed.index('href') + 7
            finish = feed[start:].index('"')
            vidurl = feed[start : start+finish]
            vidurl = "".join("http://www.archive.org/" + vidurl)
            a = self.processSpecific(vidurl)
            for element in a :
                if 'IAD.playlists' in element:
                    thumbElement = a[element][0]
                    thumbElement = thumbElement.rsplit('}')
                    dictio = thumbElement[0]
                    a = dictio.find("server'    :")
                    b = dictio.find('mp4s')
                    c = dictio[a:b]
                    c = c.rsplit('"')[1]
                    server = c
                    a = dictio.find("'thumbs'    :")
                    b = dictio.find("'srts'")
                    c = dictio[a:b]
                    c = c.rsplit('"')
                    address = c[1].replace("\\", "")
                    template = "".join('http://' + server + address)
                    self._retrieveImage(template)
            return self.thumblist
        except :
            return "hm"

    def _newSearch(self, feed):
        self._retrieveImage(feed)
        title = self._getName(feed)

    def _getName(self, feed):
        if 'href="/details/' in feed :
           part = feed[feed.index('href="/details/'):]
           part = part.split('">')
           part = part[0][15:]
           return part

    def _getThumbUrl(self, feed):
        if 'src="/serve/' in feed :
            part = feed[feed.index('src="/serve/'):]
            part = part.split('" alt=')
            part = part[0][5:]
            return part

    def _retrieveImage(self, template):
        self._retrieveThumb(template)


    def _retrieveThumb(self, template):
        a = urlretrieve(template)
        return a

    def _getSpecificVideo(self, feed):
        try :
            vidurl = feed
            vidurl = "".join("http://www.archive.org/details/" + vidurl)
            a = self.processSpecific(vidurl)
            for element in a :
                if "href" in element and 'href="/download' in a[element][0]:
                    start = a[element][0].index('href="/download')
                    finish = a[element][0][start:].index('</p>')
                    self.videoRaw = a[element][0][start - 80 : start + finish]
            return self.videoRaw, vidurl
        except :
            return None

    def process(self, query, page = 1):
        template = "".join("http://www.archive.org/search.php?query=" +
             query +"%20AND%20mediatype%3Amovies&page=" + str(page))
        print template
        request = Request(template, None, std_headers)
        try:
            video_info_webpage = urlopen(request).read()
            video_info = parse_qs(video_info_webpage)
            return video_info
        except (URLError, HTTPException, error), err:
            return None

    def processSpecific(self, url):
        request = Request(url, None, std_headers)
        try:
            video_info_webpage = urlopen(request).read()
            video_info = parse_qs(video_info_webpage)
            return video_info
        except (URLError, HTTPException, error), err:
            return None

    def _retrieveThumbnail(self, url):
        self.thumbnail = urlretrieve(url)
        return self.thumbnail

class linkParser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag=='a':
            self.links.append(dict(attrs)['href'])

class MultiDownloader(Signallable):
    """Pass a destination path and a target url to this class,
    and use current and total attributes for progress"""
    __signals__ = {
        'progress' : [],
        'finished' : [],
        }
    def __init__(self):
        self.current = 0
        self.total = 1
        self.sent = 0
        self.count = 0

    def _emitFinish(self):
        self.current = self.total
        return False

    def download(self, url,uri):
        """download using gio"""
        self.uri = uri
        self.path = urlparse(uri).path
        if os.path.exists(self.path):
            os.remove(self.path)
        dest = gio.File(uri)
        stream = gio.File(url)
        self.canc = gio.Cancellable()
        stream.copy_async(dest, self._downloadFileComplete,
            progress_callback = self._progressCb, cancellable = self.canc)

    def _progressCb(self, current, total):
        self.current = float(current)
        self.total = float(total)
        self.emit('progress')
    def _downloadFileComplete(self, gdaemonfile, result):
        self.uri = "file://" + self.uri
        self.emit("finished")

if __name__ == '__main__':
    test = WebArchiveIE()
    timestart = time.time()
    url = test.main("blue")
