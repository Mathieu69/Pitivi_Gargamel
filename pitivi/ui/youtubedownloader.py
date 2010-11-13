import urllib
import urllib2
import httplib
import socket
import gio, gtk, os, gobject
import gdata.youtube
import gdata.youtube.service
import thread
from urlparse import urlparse
import time
from pitivi.utils import beautify_length
import gst
import cgi
from tempfile import TemporaryFile

from pitivi.sourcelist import SourceListError
from pitivi.configure import get_pixmap_dir

(COL_SHORT_TEXT,
 COL_ICON,
 COL_TOOLTIP) = range(3)

try:
	from urlparse import parse_qs
except ImportError:
	from cgi import parse_qs

from pitivi.configure import LIBDIR

std_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.11) Gecko/20101019 Firefox/3.6.11',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
}

class Downloader(object):

    def __init__(self, instance):
        self.app = instance
        self._createUi()
        self.yt_service = gdata.youtube.service.YouTubeService()
        self.yt_service.ssl = False
        self.downloading = 0
        self._packed = 0
        self.toggled = 1
        self.thumbnail_list = []
        self.pixdir = os.path.join(get_pixmap_dir(),"YouTube/")

    def _downloadFile(self):
        """Download the file using gio"""

        self.builder.get_object("vbox1").remove(self.builder.get_object("entry1"))
        self.builder.get_object("vbox1").remove(self.builder.get_object('hbuttonbox2'))
        self.builder.get_object("label1").set_text("Choose a folder to save the clip in")
        self.builder.get_object("vbox1").remove(self.builder.get_object("scrolledwindow1"))
        if self.app.current.uri and self.toggled:
            dest = self.app.current.uri
            dest = dest.rsplit("/", 1)
            dest = dest[0][7:]
            dest = (dest + "/" + self.video_title)
            "".join(dest)
            self.path = urlparse(dest).path
            if os.path.exists(self.path):
                os.remove(self.path)
            self.destination = dest
            destination = gio.File(dest)
            self._createProgressBar(destination, self.template)
        else :
            self._createFileChooser()

    def _createUi(self) :
        if 'pitivi.exe' in __file__.lower():
            glade_dir = LIBDIR
        else :
            glade_dir = os.path.dirname(os.path.abspath(__file__))

        self.builder = gtk.Builder()
        gladefile = os.path.join(glade_dir, "youtubedownloader.glade")
        self.builder.add_from_file(gladefile)
        self.builder.connect_signals(self)
        self._entry1 = self.builder.get_object("entry1")
        self._entry1.connect('button-press-event', self._deleteTextCb)
        
        combo = gtk.combo_box_new_text()
        self.builder.get_object('hbuttonbox2').pack_start(combo)
        combo.show()
        combo.append_text("Choose another page..")
        for n in range(1,10):
            combo.append_text("page %s" % (str(n)))
        combo.set_active(1)
        combo.connect("changed", self._pageChangedCb)

    def _retrieveThumbnail(self, url):
        self.thumbnail = gtk.gdk.pixbuf_new_from_file(urllib.urlretrieve(url)[0])
        return self.thumbnail

    def _createFileChooser(self):
        chooser = self.builder.get_object("filechooserwidget1")
        self.builder.get_object("vbox1").pack_start(chooser)
        self.builder.get_object("button1").show()

    def _createProgressBar(self, dest, url):
        self.builder.get_object("window1").unmaximize()
        self.builder.get_object("window1").hide()
        self.builder.get_object("window1").set_resizable(0)
        stream = gio.File(url)
        canc = gio.Cancellable()
        stream.copy_async(dest , self._downloadFileComplete, progress_callback = self._progressCb, cancellable = canc)
        self.timestarted = time.time()
        self._progressBar = gtk.ProgressBar()
        self.previous_current = 0
        self.previous_timediff = 0
        self.count = 0
        self._progressBar.set_size_request(300, -1)
        self.align = gtk.Alignment(0.5, 0.5, 0, 0)
        self.align.add(self._progressBar)
        self.app.gui.sourcelist.pack_end(self.align)
        self.align.show()
        self.align.show_all()

    def _downloadFileComplete(self, gdaemonfile, result):
        """Method called after the file has downloaded"""
        uri = "file://" + self.destination
        "".join(uri)
        uri = [uri]
        try:
            self.app.current.sources.addUris(uri)
        except SourceListError as error:
            pass
        self.align.destroy()
        self.builder.get_object("window1").destroy()
        self.downloading = 0

    def _makeGDataQuery(self, _userquery, page = 0) :
        self._userquery = _userquery
        self.videoids_list = []
        self.title_list = []
        self.duration_list = []
        self.thumbnail_list = []
        self.storemodel = gtk.ListStore(str, gtk.gdk.Pixbuf, str)

        self.builder.get_object("window1").maximize()
        self.builder.get_object("window1").set_resizable(1)
        self.iconview = self.builder.get_object("iconview2")
        self.builder.get_object("entry1").set_text("Double-click a video or search another one...")
        self.builder.get_object("label1").set_text("Here are the videos that matched your query :")

        self.iconview.set_model(self.storemodel)
        self.iconview.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.iconview.set_text_column(COL_SHORT_TEXT)
        self.iconview.set_pixbuf_column(COL_ICON)
        self.iconview.set_tooltip_column (COL_TOOLTIP)

        if self._packed == 0:
            _scrolledWindow = self.builder.get_object("scrolledwindow1")
            self.builder.get_object("vbox1").pack_start(_scrolledWindow)
            self.builder.get_object("vbox1").pack_start(self.builder.get_object('hbuttonbox2')
            , expand = False, fill = False)
            self.builder.get_object("label1").show()
            self._packed = 1
            self.iconview.set_property("has_tooltip", True)


        _query = gdata.youtube.service.YouTubeVideoQuery(text_query = _userquery)
        _query.start_index = page * 50 + 1
        _query.max_results = 50
        self.feed = self.yt_service.GetYouTubeVideoFeed(_query.ToUri())
        self.cnt = 0
        if self.cnt < len (self.feed.entry):
            thread.start_new_thread(self._displayVideoSearch, (self.feed.entry[self.cnt],))
            self.cnt = self.cnt +1
        else :
            self.builder.get_object("label1").set_text("No video matched your query !")
            self.builder.get_object("entry1").set_sensitive(1)

    def _displayVideoSearch(self, entry):
        try :
            _video_link = entry.GetSwfUrl()
        except KeyError :
            if self.cnt < len (self.feed.entry):
                thread.start_new_thread(self._displayVideoSearch, (self.feed.entry[self.cnt],))
            self.cnt = self.cnt +1
            return
        try :
            index = _video_link.index("?")
        except AttributeError:
            if self.cnt < len (self.feed.entry):
                thread.start_new_thread(self._displayVideoSearch, (self.feed.entry[self.cnt],))
            self.cnt = self.cnt +1
            return
        self.videoids_list.append(_video_link[index-11 : index])
        title = entry.media.title.text
        l = len(title)
        div = l/30
        for e in range(1, div):
            title = title[:e*30] + "\n" + title[e*30:]
        self.title_list.append(title)
        display_title = title[:20]
        try :
            title = cgi.escape(title).encode( "utf-8" )
        except UnicodeDecodeError :
            pass
        duration = entry.media.duration.seconds
        self.duration_list.append(duration)
        tooltip = title + "\n" + "duration : %.0f seconds" % (float(duration))
        try :
            thumb = self._retrieveThumbnail(entry.media.thumbnail[0].url)
        except :
            if self.cnt < len (self.feed.entry):
                thread.start_new_thread(self._displayVideoSearch, (self.feed.entry[self.cnt],))
            self.cnt = self.cnt +1
            return
        self.thumbnail_list.append(thumb)
        self.storemodel.append([ display_title, thumb, tooltip])
        if self.cnt < len (self.feed.entry):
            thread.start_new_thread(self._displayVideoSearch, (self.feed.entry[self.cnt],))
            self.cnt = self.cnt +1
        else :
            self.builder.get_object("entry1").set_sensitive(1)

    def _itemActivatedCb (self, data, data2):
        _reference = data2[0]
        self.video_id = self.videoids_list[_reference]
        self.video_title = self.title_list[_reference]
        self._info = self._getInfo()
        video_fmt = self._info['fmt_map'][0][:2]
        video_token = self._info['token'][0]
        self.template = 'http://www.youtube.com/get_video?video_id=%s&t=%s&eurl=&el=&ps=&asv=&fmt=%s' % (self.video_id, video_token, video_fmt)
        if not self.downloading :
            self._downloadFile()
            self.downloading = 1
        else :
            pass

    def _getInfo(self):
        for el_type in ['&el=embedded', '&el=detailpage', '&el=vevo', '']:
            video_info_url = ('http://www.youtube.com/get_video_info?&video_id=%s%s&ps=default&eurl=&gl=US&hl=en'
                       % (self.video_id, el_type))
            request = urllib2.Request(video_info_url, None, std_headers)
            try:
                video_info_webpage = urllib2.urlopen(request).read()
                video_info = parse_qs(video_info_webpage)
                if 'token' in video_info:
                    return video_info
            except (urllib2.URLError, httplib.HTTPException, socket.error), err:
                return
        if 'token' not in video_info:
            if 'reason' in video_info:
                self._downloader.trouble(u'ERROR: YouTube said: %s' % video_info['reason'][0].decode('utf-8'))
            else:
                self._downloader.trouble(u'ERROR: "token" parameter not in video info for unknown reason')
        return

        return video_info
    def _newSearch(self, page = 0):
        urllib.urlcleanup()
        self._entry1.set_sensitive(0)
        self._entry1.set_text("Searching...")
        self._makeGDataQuery(self._userquery, page)


    def _uriChosenCb(self, data):
        self.uri = data.get_current_folder()

    def _downloadFileCb(self, dest):
        try :
            dest = self.uri
        except :
            pass
        self.builder.get_object("button1").hide()
        dest = (dest + "/" + self.video_title)
        "".join(dest)
        self.destination = dest
        self.path = urlparse(dest).path
        if os.path.exists(self.path):
            os.remove(self.path)
        destination = gio.File(dest)
        chooser = self.builder.get_object("filechooserwidget1")
        self.builder.get_object("vbox1").remove(chooser)
        self._createProgressBar(destination, self.template)

    def _quitImporterCb(self, unused = None):
        try :
            os.remove(self.path)
            self.builder.get_object("window1").destroy()
        except :
            self.builder.get_object("window1").destroy()

    def _searchEntryCb(self, entry1):
        self._userquery = entry1.get_text()
        self._newSearch()
    def _deleteTextCb(self, entry1, unused_event) :
        entry1.set_text("")

    def _progressCb(self, current, total) :
        current = float(current)
        total = float(total)
        fraction = (current/total)
        self._progressBar.set_fraction(fraction)
        timediff = time.time() - self.timestarted
        if timediff > 7.0 and self.count % 100 == 0:
            speed = (current-self.previous_current)/(timediff-self.previous_timediff)
            remaining_time = (total-current) / speed
            self.builder.get_object("window1").set_title("%.0f%% downloaded at %.0f Kbps" % (fraction*100, speed/1000))
            text = beautify_length(int(remaining_time * gst.SECOND))
            self._progressBar.set_text("About %s left" % text)
        if self.count == 400:
            self.previous_current = current
            self.previous_timediff = timediff
            self.count = 0
        self.count += 1
    def _pageChangedCb (self, combo):
        if combo.get_active() != 0:
            self._newSearch(combo.get_active()+1)

    def _saveInProjectFolderCb(self, unused_radiobutton):
        if self.toggled == 0:
            self.toggled = 1
        else :
            self.toggled = 0
        print self.toggled
