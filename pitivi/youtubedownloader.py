import gio, gtk, os, gobject
from urlparse import urlparse
try:
	from urlparse import parse_qs
except ImportError:
	from cgi import parse_qs
from urllib import urlcleanup, urlretrieve
import gdata.youtube
import gdata.youtube.service
from threading import Thread
import threading
from pitivi.signalinterface import Signallable
from cgi import escape
import time
from urllib2 import Request, urlopen, URLError
from httplib import HTTPException
from socket import error
import Queue
import scrapy

threadlist = ["0"] * 50
std_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.11) Gecko/20101019 Firefox/3.6.11',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
}
class Downloader2(Signallable):
    __signals__ = {
        'progress' : [],
        'finished' : [],
        }
    def __init__(self, url,uri):
        self.url = url
        self.uri = uri
        self._downloadFile()
        self.current = 0
        self.total = 1
    
    def _downloadFile(self):
        self.path = urlparse(self.uri).path
        if os.path.exists(self.path):
            os.remove(self.path)
        dest = gio.File(self.uri)
        stream = gio.File(self.url)
        self.canc = gio.Cancellable()
        stream.copy_async(dest , self._downloadFileComplete,progress_callback = self._progressCb, cancellable = self.canc)

    def _progressCb(self, current, total):
        self.current = float(current)
        self.total = float(total)
        self.emit('progress')
    def _downloadFileComplete(self, gdaemonfile, result):
        self.uri = "file://" + self.uri
        self.emit("finished")

class GDataQuerier(Signallable):
    __signals__ = {
        'info retrieved' : ["info"],
        'get infos finished' : ["info"],
        }
    def __init__(self):
        self.yt_service = gdata.youtube.service.YouTubeService()
        self.yt_service.ssl = False
        self.videoids_list = []
        self.title_list = []
        self.duration_list = []
        self.thumbnail_list = []

    def _getInfo(self, _reference):
        self.video_id = self.videoids_list[_reference]
        self.video_title = self.title_list[_reference]
        for el_type in ['&el=embedded', '&el=detailpage', '&el=vevo', '']:
            video_info_url = ('http://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en'
                       % (self.video_id, el_type))
            request = Request(video_info_url, None, std_headers)
            try:
                video_info_webpage = urlopen(request).read()
                video_info = parse_qs(video_info_webpage)
                if 'token' in video_info:
                    video_fmt = video_info['fmt_map'][0][:2]
                    video_token = video_info['token'][0]
                    self.template = 'http://www.youtube.com/get_video?video_id=%s&t=%s&eurl=&el=&ps=&asv=&fmt=%s' % (self.video_id, video_token, video_fmt)
                    return self.template, self.title_list[_reference]
            except (URLError, HTTPException, error), err:
                return
        if 'token' not in video_info:
            if 'reason' in video_info:
                self._downloader.trouble(u'ERROR: YouTube said: %s' % video_info['reason'][0].decode('utf-8'))
            else:
                self._downloader.trouble(u'ERROR: "token" parameter not in video info for unknown reason')
        return

        video_fmt = video_info['fmt_map'][0][:2]
        video_token = video_info['token'][0]
        self.template = 'http://www.youtube.com/get_video?video_id=%s&t=%s&eurl=&el=&ps=&asv=&fmt=%s' % (self.video_id, video_token, video_fmt)
        return self.template, self.title_list[_reference]

    def makeQuery(self, _userquery, page = 0):
        urlcleanup()
        _query = gdata.youtube.service.YouTubeVideoQuery(text_query = _userquery)
        _query.start_index = page * 18 + 1
        _query.max_results = 18
        self.feed = self.yt_service.GetYouTubeVideoFeed(_query.ToUri())
        if len(self.feed.entry) == 0:
            self.emit('get infos finished')
            return "no video"
        self.q = Queue.Queue()
        for item in self.feed.entry:
             self.q.put(item)
        for e in self.feed.entry :
             self._retrieveVideoInfo(self.q.get())
             self.q.task_done()
        self.q.join()
        self.emit('get infos finished')
    def _retrieveVideoInfo(self, entry):
        # Lots of errors to handle ..
        try :
            _video_link = entry.GetSwfUrl()
        except KeyError :
            self.emit("info retrieved", (None, None, None))
            return
        try :
            index = _video_link.index("?")
        except AttributeError:
            self.emit("info retrieved", (None, None, None))
            return 
        self.videoids_list.append(_video_link[index-11 : index])
        title = entry.media.title.text
        l = len(title)
        div = l/30
        for e in range(1, div):
            title = title[:e*30] + "\n" + title[e*30:]
        self.title_list.append(title)
        display_title = title[:15]
        try :
            title = escape(title).encode( "utf-8" )
        except UnicodeDecodeError :
            self.emit("info retrieved", (None, None, None))
            return
        try :
            thumb = self._retrieveThumbnail(entry.media.thumbnail[0].url)
            self.thumbnail_list.append(thumb)
        except :
            self.emit("info retrieved", (None, None, None))
            return
        duration = entry.media.duration.seconds
        self.duration_list.append(duration)
        tooltip = title + "\n" + "duration : %.0f seconds" % (float(duration))
        self.emit("info retrieved", (display_title, thumb, tooltip))
        return

    def _retrieveThumbnail(self, url):
        self.thumbnail = gtk.gdk.pixbuf_new_from_file(urlretrieve(url)[0])
        return self.thumbnail
