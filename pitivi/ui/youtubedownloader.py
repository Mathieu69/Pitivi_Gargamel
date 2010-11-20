import gtk, os, time
from pitivi.utils import beautify_length
from gst import SECOND
from pitivi.youtubedownloader import Downloader2, GDataQuerier

from pitivi.sourcelist import SourceListError
from pitivi.configure import get_pixmap_dir
from time import sleep


(COL_SHORT_TEXT,
 COL_ICON,
 COL_TOOLTIP) = range(3)

from pitivi.configure import LIBDIR

std_headers = {
    'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.11) Gecko/20101019 Firefox/3.6.11',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
}

class Downloader:
    def __init__(self, instance):
        self.app = instance
        self._createUi()
        self.downloading = 0
        self._packed = 0
        self.toggled = 1
        self.up = 1
        self.thumbnail_list = []
        self.pixdir = os.path.join(get_pixmap_dir(),"YouTube/")

    def _downloadFile(self):
        """Download the file using gio"""

        self.dictio["vbox1"].remove(self.dictio["entry1"])
        self.dictio["vbox1"].remove(self.dictio['hbuttonbox2'])
        self.dictio["label1"].set_text("Choose a folder to save the clip in")
        self.dictio["vbox1"].remove(self.dictio["scrolledwindow1"])

        if not self.downloading :
            if self.app.current.uri and self.toggled:
                dest = self.app.current.uri
                dest = dest.rsplit("/", 1)
                dest = dest[0][7:]
                dest = (dest + "/" + self.video_title)
                "".join(dest)
                self.uri = dest.rsplit("/", 1)[0]
                self.downloader = Downloader2(self.template, dest)
                self.downloader.connect("finished", self._downloadFileCompleteCb)
                self.downloader.connect("progress", self._progressCb)
                self._createProgressBar()
                self.downloading = 1
            else :
                self.builder.get_object("vbox2").remove(self.builder.get_object("vbox1"))
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

        self.dictio = {}
        for e in ["vbox1", "vbox2", "hbuttonbox1", "hbuttonbox2", "entry1",
         "label1", "scrolledwindow1","window1", "button1", "button2"]:
            self.dictio[e] = self.builder.get_object(e)
        self.dictio["entry1"].connect('button-press-event', self._deleteTextCb)

        self.combo = gtk.combo_box_new_text()
        self.dictio["hbuttonbox2"].pack_start(self.combo)
        self.combo.show()
        self.combo.append_text("Choose another page..")
        for n in range(1,10):
            self.combo.append_text("page %s" % (str(n)))
        self.combo.set_active(1)
        self.combo.connect("changed", self._pageChangedCb)

    def _createFileChooser(self):
        chooser = self.builder.get_object("filechooserwidget1")
        self.dictio["vbox2"].pack_start(chooser)
        self.dictio["vbox2"].remove(self.dictio["hbuttonbox1"])
        self.dictio["vbox2"].pack_end(self.dictio["hbuttonbox1"],
         expand = False, fill = False)
        self.dictio["button1"].show()

    def _createProgressBar(self):
        self.dictio["window1"].unmaximize()
        self.dictio["window1"].hide()
        self.dictio["window1"].set_resizable(0)
        self.timestarted = time.time()
        self._progressBar = gtk.ProgressBar()
        self.previous_current = 0
        self.previous_timediff = 0
        self.count = 0
        self._progressBar.set_size_request(220, -1)
        self.vbox = gtk.VBox()
        self.vbox.pack_end(self._progressBar, expand = False, fill = False)
        self.dictio["hbuttonbox1"].remove(self.dictio["button2"])
        self.vbox.pack_end(self.dictio["button2"], expand = False, fill = False)
        self.app.gui.sourcelist.pack_end(self.vbox, expand = False, fill = False)
        self.vbox.show()
        self.vbox.show_all()
        self.dictio["button2"].connect('clicked', self._quitImporterCb)
        self.dictio["button2"].set_label("Cancel %s" % self.video_title[:20])
        self.downloading = 1

    def _downloadFileCompleteCb(self, data):
        """Method called after the file has downloaded"""
        self.up = 0
        uri = "file://" + self.uri + "/" + self.video_title
        self.uri = uri[7:]
        "".join(uri)
        uri = [uri]
        if self.downloader.current != self.downloader.total :
            os.remove(self.uri)
        else :
            try:
                self.app.current.sources.addUris(uri)
            except SourceListError as error:
                pass

        self.vbox.destroy()
        self.dictio["window1"].destroy()
        self.app.gui.sourcelist.downloading -=1
        self.downloading = 0

    def _itemActivatedCb (self, data, data2):
        _reference = data2[0]
        self.answer = self.querier._getInfo(_reference)
        self.template = self.answer[0]
        self.video_title = self.answer[1]
        self._downloadFile()

    def _newSearch(self, page = 0):
        try :
            self.delete(self.querier)
            print "han"
        except :
            pass
        self.dictio["entry1"].set_sensitive(0)
        self.dictio["entry1"].set_text("Searching...")
        self.list = []

        self.storemodel = gtk.ListStore(str, gtk.gdk.Pixbuf, str)
        self.dictio["window1"].maximize()
        self.dictio["window1"].set_resizable(1)
        self.iconview = self.builder.get_object("iconview2")
        self.builder.get_object("entry1").set_text("Double-click a video or search another one...")
        self.builder.get_object("label1").set_text("Here are the videos that matched your query :")
        
        self.querier = GDataQuerier()
        self.querier.connect('get infos finished', self._getInfosFinishedCb)
        self.querier.connect('kill because of thread.error', self._quitImporterCb)
        result = self.querier.makeQuery(self._userquery, page)
        if result == "no video":
            self.builder.get_object("label1").set_text("No video matched your query")
            self.dictio['entry1'].set_sensitive(1)

        if self._packed == 0:
            _scrolledWindow = self.builder.get_object("scrolledwindow1")
            self.builder.get_object("vbox1").pack_start(_scrolledWindow)
            self.builder.get_object("vbox1").pack_start(self.builder.get_object('hbuttonbox2')
            , expand = False, fill = False)
            self.builder.get_object("label1").show()
            self._packed = 1
            self.iconview.set_property("has_tooltip", True)
      
        self.iconview.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.iconview.set_text_column(COL_SHORT_TEXT)
        self.iconview.set_pixbuf_column(COL_ICON)
        self.iconview.set_tooltip_column (COL_TOOLTIP)



    def _getInfosFinishedCb(self, a, info):
        self.dictio["entry1"].set_sensitive(1)
        for entry in info :
            if entry[0] == None :
                thumb = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir(),"error.png"))
                self.storemodel.append(["Error !", thumb, "Error during the retrieval"])
            else :
                self.storemodel.append([entry[0], entry[1], entry[2]])
        self.iconview.set_model(self.storemodel)

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
        chooser = self.builder.get_object("filechooserwidget1")
        self.dictio["vbox2"].remove(chooser)
        self.downloader = Downloader2(self.template, dest)
        self.downloader.connect("progress", self._progressCb)
        self.downloader.connect("finished", self._downloadFileCompleteCb)
        self.downloading = 1
        self._createProgressBar()

    def _quitImporterCb(self, unused = None):
        self.app.gui.sourcelist.downloading -=1
        try :
            self.up = 0
            self.downloader.canc.cancel()
            if self.downloader.current != self.downloader.total :
                os.remove(self.uri)
            self.dictio["window1"].destroy()
        except :
            self.up = 0
            self.dictio["window1"].destroy()

    def _searchEntryCb(self, entry1):
        self._userquery = entry1.get_text()
        self.combo.set_active(0)
        self.page = 1
        self._newSearch(0)

    def _deleteTextCb(self, entry1, unused_event) :
        entry1.set_text("")

    def _progressCb(self, data) :
        current = self.downloader.current
        total = self.downloader.total
        fraction = (current/total)
        self._progressBar.set_fraction(fraction)
        timediff = time.time() - self.timestarted
        if timediff > 7.0 and self.count % 100 == 0:
            speed = (current-self.previous_current)/(timediff-self.previous_timediff)
            remaining_time = (total-current) / speed
            self.builder.get_object("window1").set_title("%.0f%% downloaded at %.0f Kbps" % (fraction*100, speed/1000))
            text = beautify_length(int(remaining_time * SECOND))
            self._progressBar.set_text("About %s left" % text)
        if self.count == 400:
            self.previous_current = current
            self.previous_timediff = timediff
            self.count = 0
        self.count += 1
    def _pageChangedCb (self, unused_combo):
        if self.combo.get_active() != 0 and self.combo.get_active() != self.page:
            self.page = self.combo.get_active()
            self._newSearch(self.combo.get_active()-1)

    def _saveInProjectFolderCb(self, unused_radiobutton):
        if self.toggled == 0:
            self.toggled = 1
        else :
            self.toggled = 0
