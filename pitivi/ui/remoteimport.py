import gtk, os, time
from pitivi.utils import beautify_length
from gst import SECOND
from urllib2 import Request, urlopen, URLError

from pitivi.sourcelist import SourceListError
from pitivi.configure import get_pixmap_dir
from random import randrange
from urllib import urlretrieve, urlcleanup
import thread
from pitivi.remoteimport import MultiDownloader, WebArchiveIE, BlipIE
from pitivi.ui.webpreviewer import Preview
import gobject


(COL_SHORT_TEXT,
 COL_ICON,
 COL_TOOLTIP) = range(3)

from pitivi.configure import LIBDIR

class RemoteDownloader:

    def __init__(self, instance):
        self.downloading = 0
        self.app = instance
        self._createUi()
        self._packed = 0
        self.toggled = 1
        self.thumbnail_list = []
        self.pixdir = os.path.join(get_pixmap_dir(),"Remote/")
        self.previewer = 0
        self.combo2 = 0

    def _createUi(self) :
        if 'pitivi.exe' in __file__.lower():
            glade_dir = LIBDIR
        else :
            glade_dir = os.path.dirname(os.path.abspath(__file__))

        # Open UI file
        self.builder = gtk.Builder()
        gladefile = os.path.join(glade_dir, "archivedownloader.glade")
        self.builder.add_from_file(gladefile)
        self.builder.connect_signals(self)

        # Reference widgets and add a combobox to change page
        self.dictio = {}
        for e in ["vbox1", "vbox2", "hbuttonbox1", "hbuttonbox2", "entry1",
         "label1", "scrolledwindow1","window1", "button1", "button2",
         "iconview2", "button3", "button4", "spinbutton1", "hbox1"]:
            self.dictio[e] = self.builder.get_object(e)
        self.dictio["entry1"].connect('button-press-event',
         self._deleteTextCb)
        self.combo3 = gtk.combo_box_new_text()
        self.dictio['hbox1'].pack_end(self.combo3, expand = False, fill = False)
        self.combo3.show()
        self.combo3.append_text('Archive')
        self.combo3.append_text('Blip')
        self.combo3.set_active(0)
        self.combo = gtk.combo_box_new_text()
        self.dictio["hbuttonbox1"].pack_end(self.combo)
        self.combo.show()
        self.combo.append_text("Choose another page..")
        for n in range(1,10):
            self.combo.append_text("page %s" % (str(n)))
        self.combo.set_active(1)
        self.combo.connect("changed", self._pageChangedCb)
        self.combo.hide()
        self.dictio["vbox1"].pack_end(self.dictio['hbuttonbox2']
            , expand = False, fill = False)

    def blipThread(self, bogus):
        self.origin = 'blip'
        self.combo.set_active(1)
        self.blipquerier = BlipIE()
        for e in range(4):
            self.result = self.blipquerier.search(self._userquery, e + 1)
            for element in self.result :
                self.resultlist.append(element)
        self.thumburis = []
        if not len(self.resultlist):
            self.dictio['entry1'].set_sensitive(1)
            self.dictio['entry1'].set_text('Search..')
            self.dictio['label1'].set_text('No video matched your query')
            self.dictio['label1'].show()
            return
        for result in self.resultlist:
            thread.start_new_thread(self.thumbRetriever, (result,))
        gobject.timeout_add(5000, self._searchDone)

    def search(self):
        self.page = 0
        if self.combo2:
            self.combo2.destroy()
        self.dictio['entry1'].set_sensitive(0)
        self.dictio['entry1'].set_text('Searching...')
        self.querier = WebArchiveIE()
        self.resultlist = []
        if self.combo3.get_active() == 0:
            self.origin = 'archive'
            self.combo.set_active(0)
            self.combo.set_active(1)
            return
        elif self.combo3.get_active() == 1:
            thread.start_new_thread(self.blipThread, (None,))


    def mainthread(self, query):
        self.thumburis = []
        self.namelist = []
        self.thumblist = []
        filled = 0
        if self.page:
            feed = self.querier.main(query, self.page)
        else:
            feed = self.querier.main(query)
        for element in feed:
            if 'thumbCell' in feed[element][0] :
                filled = 1
        if not filled :
            self.dictio['entry1'].set_sensitive(1)
            self.dictio['entry1'].set_text('Search..')
            self.dictio['label1'].set_text('No video matched your query')
            self.dictio['label1'].show()
            return
        for element in feed:
            name = self.querier.specThumb(feed[element])
            if name != []:
                for e in name :
                    if e != None:
                        self.thumblist.append(e)
        for element in self.thumblist:
            e = element.split("/")[2]
            self.namelist.append(e)
        self.shown = 0
        self.errorCount = 0
        self.valid = 0
        count = 0
        for element in self.thumblist:
            template = "".join("http://www.archive.org" + element)
            name = self.namelist[count]
            thread.start_new_thread(self.thumbRetriever, ([name, name, template],))
            count = count + 1
        self.update = 1
        self.progresscount = 0
        gobject.timeout_add(10000, self._searchDone)

    def thumbRetriever(self, result):
        a = self.querier._retrieveThumb(result[2])
        try :
            thumb = gtk.gdk.pixbuf_new_from_file(a[0])
            thumb = thumb.scale_simple(160, 120, gtk.gdk.INTERP_NEAREST)
        except :
            thumb = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir()
        ,"error.png"))
            thumb = thumb.scale_simple(160, 120, gtk.gdk.INTERP_NEAREST)
        self.thumburis.append((thumb, result[1], result[0]))

    def _searchDone(self):
        self.combo.set_sensitive(1)
        if self.origin == 'blip':
            self.builder.get_object('button4').set_label('Download')
        self.combo.show()
        self.dictio['entry1'].set_sensitive(1)
        self.dictio['entry1'].set_text('Search..')
        self.update = 0

        self.storemodel = gtk.ListStore(str, gtk.gdk.Pixbuf, str)
        self.builder.get_object("label1").set_text(
            "Here are the videos that matched your query :")

        self.dictio["iconview2"].set_orientation(gtk.ORIENTATION_VERTICAL)
        self.dictio["iconview2"].set_text_column(COL_SHORT_TEXT)
        self.dictio["iconview2"].set_pixbuf_column(COL_ICON)
        self.dictio["iconview2"].set_tooltip_column (COL_TOOLTIP)
        self.dictio["button3"].show()
        self.dictio["button4"].show()
        self.dictio["button3"].set_sensitive(0)
        self.dictio["button4"].set_sensitive(0)
        count = 0
        self.dictio["iconview2"].set_model(self.storemodel)
        self.thumburis.reverse()
                # If it's the first search, we keep the same window
        if self._packed == 0:
            self.dictio["window1"].set_resizable(1)
            self.dictio["window1"].resize(1024, 768)
            _scrolledWindow = self.builder.get_object("scrolledwindow1")
            self.builder.get_object("vbox1").pack_start(_scrolledWindow)
            self.builder.get_object("label1").show()
            self._packed = 1
            self.dictio["iconview2"].set_property("has_tooltip", True)
        for e in self.thumburis :
            name = e[1]
            self.storemodel.append([name[:15], e[0], name])
            count += 1
        self.dictio["iconview2"].set_columns(5)

    def _chooseMode(self):
        downloader = DownloaderUI(self.app)
        if self.app.current.uri and self.toggled:
            dest = self.app.current.uri
            dest = dest.rsplit("/", 1)[0]
            dest = dest[7:]
 
            self.video_title = self.link.rsplit("/", 1)[1]
            dest = (dest + "/" + self.video_title)
            self.app.gui.sourcelist.downloading +=1
            self.app.gui.sourcelist.importerUp = 0
            self.preview = 0
            self.downloading = 1
            downloader.download(self.link, dest)
            self.dictio["window1"].destroy()
        else:
            downloader._createFileChooser(self.link, self)

    def _changeBlipPage(self):
        self.combo.set_sensitive(0)
        self.dictio['entry1'].set_sensitive(0)
        self.dictio['entry1'].set_text('Searching...')
        self.querier = WebArchiveIE()
        self.blipquerier = BlipIE()
        self.resultlist = []
        for e in range(4):
            self.result = self.blipquerier.search(self._userquery, e + 1 + self.page)
            for element in self.result :
                self.resultlist.append(element)
        self.blipThread()

    def _searchEntryCb(self, entry1):
        self._userquery = entry1.get_text()
        self.search()

    def _deleteTextCb(self, entry1, unused_event) :
        if entry1.get_text() == 'Search..':
            entry1.set_text("")

    def _pageChangedCb (self, unused_combo):
        if self.combo.get_active() != 0 and self.combo.get_active() != self.page:
            self.page = self.combo.get_active()
            if self.origin == 'blip':
                self._changeBlipPage()
                return
            thread.start_new_thread(self.mainthread, (self._userquery,))

    def _saveInProjectFolderCb(self, unused_radiobutton):
        if self.toggled == 0:
            self.toggled = 1
        else :
            self.toggled = 0

    def _previewCb(self, unused_button):
        ref = self.preview_reference[0][0]
        if self.origin == 'archive':
            feed = self.thumburis[self.preview_reference[0][0]][1]
            links = self.querier.getLinks(feed)

            link = links[0][0]
            self.template = "".join("http://www.archive.org" + link)

        if self.origin == 'blip'and len(self.preview_reference):
            info = self.thumburis[self.preview_reference[0][0]][2]
            filename = self.blipquerier.getVideoUrl(info)
            self.template =''.join('http://blip.tv/file/get/' + filename + '?referrer=blip.tv&source=1&use_direct=1&use_documents=1')

        if self.previewer == 0:
            self.viewer = Preview(self.template, self, ref)
            self.previewer = 1

    def _changeCb(self, ref):
        if self.origin == 'blip':
            info = self.resultlist[ref]
            info = self.thumburis[ref][2]
            filename = self.blipquerier.getVideoUrl(info)
            self.template =''.join('http://blip.tv/file/get/' + filename + '?referrer=blip.tv&source=1&use_direct=1&use_documents=1')
        return self.template

        feed = self.thumburis[ref][1]
        links = self.querier.getLinks(feed)
        link = links[0][0]
        self.template = "".join("http://www.archive.org" + link)
        return self.template

    def _downloadSelectedCb(self, unused_button):
        if self.origin == 'blip':
            self.format = 1
        if not self.format :
            self.dictio["button4"].set_label('Download')
            self.combo2 = gtk.combo_box_new_text()
            self.dictio['hbuttonbox2'].pack_end(self.combo2, expand = False)
            self.combo2.show()
            feed = self.thumburis[self.preview_reference[0][0]][1]
            ref = self.preview_reference[0][0]
            links = self.querier.getLinks(feed)

            for link in links[0] :
                self.combo2.append_text(link)
            self.combo2.set_active(0)
            self.format = 1
            return
        if self.origin == 'archive':
            self.link = "".join("http://www.archive.org" + self.combo2.get_active_text())
            self._chooseMode()
        if self.origin == 'blip' and len(self.preview_reference):
            self.link = self.resultlist[self.preview_reference[0][0]]
            self.link = self.thumburis[self.preview_reference[0][0]][2]
            filename = self.blipquerier.getVideoUrl(self.link)
            self.link =''.join('http://blip.tv/file/get/' + filename + '?referrer=blip.tv&source=1&use_direct=1&use_documents=1')
            self._chooseMode()

    def _itemActivatedCb (self, data, data2):
        _reference = data2[0]

    def _selectionChangedCb(self, iconview):
        self.format = 0
        self.preview_reference = iconview.get_selected_items()
        if self.origin == 'archive':
            self.dictio["button4"].set_label('Choose a format')

        if len(self.preview_reference):
            self.shown = 1
        else:
            self.shown = 0

        if self.shown == 1:
            self.dictio["button3"].set_sensitive(1)
            self.dictio["button4"].set_sensitive(1)
        elif self.shown == 0:
            self.dictio["button3"].set_sensitive(0)
            self.dictio["button4"].set_sensitive(0)
        if self.combo2 :
            self.combo2.destroy()

    def _cancelButtonCb(self, unused_button):
        # Will call _quitImporterCb
        self.dictio["window1"].destroy()

    def _quitImporterCb(self, unused = None):
        """Decrement the download count and try to remove
        all current downloads before quitting"""
        # Update the download counts and up reference
        self.app.gui.sourcelist.importerUp = 0

        if self.previewer :
            self.viewer.window.destroy()
        if self.downloading == 1:
            self.app.gui.sourcelist.downloading -=1
        try :
            self.downloader.canc.cancel()
            if self.downloader.current != self.downloader.total :
                os.remove(self.uri)
            self.dictio["window1"].destroy()
        except :
            self.dictio["window1"].destroy()

class DownloaderUI:
    def __init__(self, app):
        self.app = app

    def _createFileChooser(self, link, instance):
        self.instance = instance
        if 'pitivi.exe' in __file__.lower():
            glade_dir = LIBDIR
        else :
            glade_dir = os.path.dirname(os.path.abspath(__file__))
        self.link = link
        self.video_title = self.link.rsplit("/", 1)[1]

        self.builder = gtk.Builder()
        gladefile = os.path.join(glade_dir, "downloader_ui.glade")
        self.builder.add_from_file(gladefile)
        self.builder.connect_signals(self)

    def download(self, url, uri):
        self.video_title = url.rsplit("/", 1)[1]
        self.url = url
        self.uri = uri
        self.downloader = MultiDownloader()
        self.downloader.download(url, uri)
        self.downloader.connect("finished", self._downloadFileCompleteCb)
        self.downloader.connect("progress", self._progressCb)
        self._createProgressBar()

    def _createProgressBar(self):
        # Keep a time reference for the progress bar
        self.timestarted = time.time()
        self._progressBar = gtk.ProgressBar()
        self.previous_current = 0
        self.previous_timediff = 0
        self.count = 0
        self._progressBar.set_size_request(220, -1)
        self._cancelButton = gtk.Button('Cancel')
        self._cancelButton.show()
        self._cancelButton.connect('clicked', self._cancelButtonCb)
        self.vbox = gtk.VBox()
        self.vbox.pack_end(self._progressBar, expand = False, fill = False)
        self.vbox.pack_end(self._cancelButton)
        # Pack the bar in the sourcelist. Should stay in this window if more
        # than 3 simultaneous downloads are wanted.
        self.app.gui.sourcelist.pack_end(self.vbox,
        expand = False, fill = False)
        self.vbox.show()
        self.vbox.show_all()

    def _quitFileChooserCb(self, unused_button):
        self.builder.get_object('filechooserdialog1').destroy()

    def _downloadFileCb(self, unused_button):
        self.instance.app.gui.sourcelist.downloading +=1
        self.instance.app.gui.sourcelist.importerUp = 0
        self.instance.preview = 0
        self.instance.downloading = 1
        dest = self.builder.get_object('filechooserdialog1').get_filename()
        dest = (dest + "/" + self.video_title)
        self.dest = dest
        self.builder.get_object('filechooserdialog1').destroy()
        self.instance.dictio['window1'].destroy()
        self.download(self.link, dest)

    def _progressCb(self, data) :
        current = self.downloader.current
        total = self.downloader.total
        fraction = (current/total)
        self._progressBar.set_fraction(fraction)
        timediff = time.time() - self.timestarted

        if timediff > 7.0 and self.count % 100 == 0:
            speed = (current-self.previous_current)/(timediff
            -self.previous_timediff)
            remaining_time = (total-current) / speed
            text = beautify_length(int(remaining_time * SECOND))
            self._progressBar.set_text("About %s left" % text)

        if self.count == 400:
            self.previous_current = current
            self.previous_timediff = timediff
            self.count = 0
        self.count += 1

    def _downloadFileCompleteCb(self, data):
        if self.downloader.current == self.downloader.total :
            uri = "file://" + self.uri
            self.uri = uri[7:]
            #"".join(uri)
            uri = [uri]
            try:
                self.app.current.sources.addUris(uri)
            except SourceListError as error:
                pass
        self.vbox.destroy()

    def _cancelButtonCb(self, unused_button):
        self.downloader.canc.cancel()
        if self.downloader.current != self.downloader.total :
            os.remove(self.dest)
