import gtk, os, time
from pitivi.utils import beautify_length
from gst import SECOND, STATE_NULL
from urllib2 import Request, urlopen, URLError
import gobject
from gettext import gettext as _

from pitivi.sourcelist import SourceListError
from pitivi.configure import get_terms_dir
from pitivi.configure import get_pixmap_dir
from random import randrange
from urllib import urlretrieve, urlcleanup
import thread
from pitivi.remoteimport import MultiDownloader, WebArchiveIE, BlipIE
from pitivi.ui.webpreviewer import Preview
from pitivi.settings import GlobalSettings

(TERMS_NOT_ACCEPTED,
 TERMS_ACCEPTED) = range(2)

(COL_SHORT_TEXT,
 COL_ICON,
 COL_TOOLTIP) = range(3)

from pitivi.configure import LIBDIR

class TermsAcceptance:
    def __init__(self, app, instance, platform):
        self.settings = app.settings
        self.platform = platform
        self.app = app
        if platform == 'blip':
            terms = '/blipterms'
        else :
            terms = '/archiveterms'
        self.instance = instance
        self._createUI(terms)

    def _createUI(self, terms):
        if 'pitivi.exe' in __file__.lower():
            glade_dir = LIBDIR
        else :
            glade_dir = os.path.dirname(os.path.abspath(__file__))

        # Open UI file
        self.builder = gtk.Builder()
        gladefile = os.path.join(glade_dir, "terms.glade")
        self.builder.add_from_file(gladefile)
        self.builder.connect_signals(self)
        self.termsdir = get_terms_dir()
        self.builder.get_object('dialog1').set_transient_for(self.app.gui)
        self._openTerms(terms)

    def _openTerms(self, terms):
        terms_file = "".join(self.termsdir + terms)
        terms_text = open(terms_file, 'r')
        terms_text = terms_text.read()
        self._appendText(terms_text)

    def _appendText(self, terms_text):
        textbuffer = gtk.TextBuffer()
        textbuffer.set_text(terms_text)
        self.builder.get_object('textview1').set_buffer(textbuffer)

    def _acceptedCb(self, unused_button):
        self.builder.get_object('dialog1').destroy()
        if self.platform == 'archive':
            self.instance.realShowImportFromRemoteDialog()
            self.settings.archiveTerms = TERMS_ACCEPTED
        else :
            self.settings.blipTerms = TERMS_ACCEPTED
            self.instance.combo3.set_active(1)

    def _rejectedCb(self, unused_button):
        self.builder.get_object('dialog1').destroy()


class RemoteDownloader:

    def __init__(self, app, instance):
        self.thumburis = []
        self._userquery = 0
        self.threadserial = 0
        self.viewer = 0
        self.downloading = 0
        self.searching = 0
        self.waiting = 0
        self.reallyNothingCount = 0
        self._previousquery = self.previous_origin = self.origin = ""
        self.up = 1
        self.refreshing = 0
        self.previewer = 0
        self.app = app
        self._packed = 0
        self.toggled = 1
        self.combo2 = 0
        self.instance = instance
        self.lock = thread.allocate_lock()
        self.settings = self.app.settings
        self.pixdir = "".join(get_pixmap_dir() + '/Remote/')
        self._createUi()
        self.waitingthreads = 0
        self.viewer = Preview(None , self, 0, app.gui)

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
         "scrolledwindow1","window1", "button1", "button2","statusbar1",
         "iconview2", "button3", "button4", "spinbutton1", "hbox1"]:
            self.dictio[e] = self.builder.get_object(e)
        self.context = self.dictio['statusbar1'].get_context_id('bottom')
        self.dictio["entry1"].connect('button-press-event',
         self._deleteTextCb)
        self.combo3 = gtk.combo_box_new_text()          #Platform chooser combobox
        self.dictio['hbox1'].pack_end(self.combo3)
        self.dictio['hbox1'].reorder_child(self.combo3, 2)
        self.combo3.show()
        self.combo3.append_text('Archive')
        self.combo3.append_text('Blip')
        self.combo3.set_active(0)
        self.dictio['window1'].set_transient_for(self.app.gui)

        self.dictio['iconview2'].set_column_spacing(0)
        self.dictio['iconview2'].set_row_spacing(0)
        self.throbber = gtk.Image()
        pixdir = get_pixmap_dir() + '/busy.gif'
        print pixdir
        self.throbber.set_from_file(pixdir)
        self.builder.get_object('hbox1').pack_end(self.throbber)
        self.throbber.hide()
        self.builder.get_object('vbox4').pack_end(self.builder.get_object('checkbutton1'), expand = False, fill = False)
        if self.settings.blipTerms == TERMS_NOT_ACCEPTED :
            self.combo3.connect('changed', self._blipTermsCb)

        self.dictio["window1"].set_resizable(1)
        self.dictio["window1"].resize(900, 600)
        self.dictio["window1"].set_icon_from_file("".join(self.pixdir + "prometheusflame.png"))

        self.builder.get_object('image1').set_from_file("".join(self.pixdir + "banner.png"))

        self.combo3.set_active(self.settings.source)

    def _refresh(self):
        self.page += 1
        self.refreshing = 1
        self.search()

    def _maybeRefresh(self):
        if not self.stopSearch:
            self._refresh()
        else:
            self._searchDone()

    def _continuousSearch(self, button):
        self._userquery = "+".join(self.dictio['entry1'].get_text().split())
        self.builder.get_object('label6').hide()
        if self._userquery != "" and self._userquery != self._previousquery:
            self.page = 0
            self.refreshing = 0

        elif self._userquery == '':
            self.dictio['statusbar1'].push(self.context, _("I can't search for nothing !"))
            button.set_active(False)
            return
        if self._userquery == self._previousquery and self.previous_origin == self.combo3.get_active_text().lower():
            self.page += 1
            self.refreshing = 1
        else :
            self.page = 0
            self.refreshing = 0
            self.coeff = 1
            print "put"
            self.viewer.player.set_state(STATE_NULL)
            self.viewer.viewer.playpause_button.set_sensitive(False)
        self._previousquery = self._userquery

        if button.get_label() == 'Go !' or button.get_label() == 'More results':
            button.set_label('Stop')
            self.stopSearch = 0
            self.search()
        else :
            self.page -= 1
            self.stopSearch = 1
            button.set_label('More results')
            print "pute"
            self.waiting = 1
            button.set_sensitive(0)

    def search(self):
        """ Common search function for both platforms and pages"""
        print len(self.thumburis)
        self.previous_origin = self.origin
        self.dictio["button4"].show()
        self.cnt = 0
        self.thumbcnt = 0
        self.searching = 1

        if not self.refreshing :
            self.index = 0
            self.storemodel = gtk.ListStore(str, gtk.gdk.Pixbuf, str)
            self.dictio["iconview2"].set_model(self.storemodel)
            print 'wtf'

        self.combo3.hide()
        self.throbber.show()
        self.dictio["iconview2"].set_orientation(gtk.ORIENTATION_VERTICAL)
        self.dictio["iconview2"].set_text_column(COL_SHORT_TEXT)
        self.dictio["iconview2"].set_pixbuf_column(COL_ICON)
        self.dictio["iconview2"].set_tooltip_column (COL_TOOLTIP)
        self.builder.get_object("statusbar1").show()

        if not self._packed:
            self.builder.get_object("image1").hide()
            hbox = self.builder.get_object("hbox2")
            self.builder.get_object("vbox1").pack_start(hbox)
            self._packed = 1
            self.dictio["iconview2"].set_property("has_tooltip", True)
            self.dictio["iconview2"].set_columns(-1)
        if self.combo2 and not self.refreshing:     #FIXME : No easy way to clear a combobox created
            self.combo2.destroy()                   #with the convenience function.
        self.dictio['entry1'].set_sensitive(0)
        self.builder.get_object("statusbar1").push(self.context,
            _("Trying to grab page %i for query %s ...") % (self.page + 1, self._userquery))

        if not self.refreshing :
            self.querier = WebArchiveIE()
            self.resultlist = []
        self.settings.source = self.combo3.get_active()
        print self.refreshing, 'jhbj'
        if self.combo3.get_active() == 0 and self.up:
            self.origin = 'archive'
            thread.start_new_thread(self.archiveThread, (self._userquery,))
            return
        elif self.combo3.get_active() == 1 and self.up:
            thread.start_new_thread(self.blipThread, (None,))
        if len(self.thumburis) / self.coeff > 50:
            self.builder.get_object('togglebutton1').set_active(0)
            self.coeff += 1
            self.refreshing = 0

    def preview(self):
        self.builder.get_object('label2').set_text("Loading video")
        thread.start_new_thread(self._preview, (None,))

    def blipThread(self, bogus):
        if not self.refreshing :
            self.thumburis = []
            self.blipquerier = BlipIE()
        self.origin = 'blip'
        self.result = self.blipquerier.search(self._userquery, self.page + 1)
        if self.result is not None :
            for element in self.result :
                self.resultlist.append(element)
        else:
            self._maybeRefresh()
            return

        if len(self.resultlist) == 0:
            self.reallyNothingCount += 1
            print self.reallyNothingCount, 'ok'
            if self.reallyNothingCount == 4:
                self.builder.get_object('togglebutton1').set_active(0)
            self._maybeRefresh()
            return
        else :
            self.reallyNothingCount = 0

        for result in self.resultlist[self.index:]:
            if self.up:
                self.lock.acquire()
                thread.start_new_thread(self.thumbRetriever, (result, self.threadserial))
                self.lock.release()
        gobject.timeout_add(50, self._update)

    def archiveThread(self, query):
        if not self.refreshing:
            self.thumburis = []
            self.namelist = []
            self.thumblist = []
        filled = 0

        if self.page:
            feed = self.querier.main(query, self.page + 1)
        else:
            feed = self.querier.main(query)
        for element in feed:
            if 'thumbCell' in feed[element][0] :
                filled = 1

        if not filled :
            self.reallyNothingCount += 1
            print self.page, 'put'
            if self.reallyNothingCount == 5:
                if self.page == 4:
                    self.dictio['statusbar1'].push(self.context, _('No videos'))
                else :
                    self.dictio['statusbar1'].push(self.context, _('No more videos'))
                self.reallyNothingCount = 0
                self.builder.get_object('togglebutton1').set_active(False)
                self.builder.get_object('togglebutton1').set_sensitive(0)
                self.stopSearch = 1

            else :
                self._maybeRefresh()
                return
        else :
            self.reallyNothingCount = 0

        for element in feed:
            name = self.querier.specThumb(feed[element])
            if name != []:
                for e in name :
                    if e != None:
                        self.thumblist.append(e)

        for element in self.thumblist[self.index:]:
            e = element.split("/")[2]
            self.namelist.append(e)
        self.shown = 0
        count = 0

        if self.stopSearch:
            self._searchDone()
            return
        self.threadserial += 1
        for element in self.thumblist[self.index:]:
            template = "".join("http://www.archive.org" + element)
            if count + self.index < len (self.namelist):
                name = self.namelist[count + self.index]
                self.lock.acquire()
                if self.up :
                    thread.start_new_thread(self.thumbRetriever, ([name, name, template], self.threadserial))
                self.lock.release()
                count = count + 1

        self.progresscount = 0
        gobject.timeout_add(50, self._update)

    def _update(self):
        self.lock.acquire()
        cnt = 0
        if self.index == len(self.thumburis) and self.index > 0: #Start nothing new counter
            self.nothingcnt += 1
        else :
            self.nothingcnt = 0
        for e in self.thumburis[self.index:]:
            cnt += 1
            name = e[1]
            try :
                self.storemodel.append([name[:15], e[0], name])
            except :
                pass
        self.index = self.index + cnt
        self.lock.release()
        self.cnt += 1

        if self.cnt == 200 and self.origin == 'blip':
            self.reallyNothingCount += 1
            print self.reallyNothingCount, 'chier'
            if self.reallyNothingCount == 4:
                if self.page == 4:
                    self.dictio['statusbar1'].push(self.context, _('No videos'))
                else :
                    self.dictio['statusbar1'].push(self.context, _('No more videos'))
                self.reallyNothingCount = 0
                self.builder.get_object('togglebutton1').set_active(False)
                self.builder.get_object('togglebutton1').set_sensitive(0)
                self.stopSearch = 1

            else :
                self._maybeRefresh()
                return
        if self.origin == 'blip' and self.nothingcnt == 5: # 0.25 seconds
            self.reallyNothingCount = 0
            self._maybeRefresh()
            return
        if self.nothingcnt == 50 and not self.stopSearch: # 2.5 seconds elapsed with nothing new
            self.reallyNothingCount = 0
            self._maybeRefresh()
            return
        elif self.nothingcnt == 50 and self.stopSearch:
            self._searchDone()
            return
        if self.nothingcnt == 50:
            self._maybeRefresh()
            return
        elif self.stopSearch:
            self._searchDone()
            return
        gobject.timeout_add(50, self._update)

    def thumbRetriever(self, result, serial):
        a = self.querier._retrieveThumb(result[2])
        try :
            thumb = gtk.gdk.pixbuf_new_from_file(a[0])
            if self.origin == 'blip':
                thumb = thumb.scale_simple(159, 130, gtk.gdk.INTERP_BILINEAR)
        except :
            thumb = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir()
        ,"error.png"))
            thumb = thumb.scale_simple(159, 130, gtk.gdk.INTERP_BILINEAR)
        name = result[1]
        if serial == self.threadserial and self.origin == 'archive':
            self.thumburis.append((thumb, result[1], result[0]))
        elif serial == self.threadserial and self.origin == 'blip' and len(result) > 3:
            self.thumburis.append((thumb, result[1], result[0], result[3]))
        elif serial == self.threadserial and self.origin == 'blip':
            self.thumburis.append((thumb, result[1], result[0], "Duration unavailable"))

    def _searchDone(self):
        self.pagecnt = 0
        self.threadserial += 1
        self.searching = 0
        self.reallyNothingCount = 0
        if self.waiting:
            self.builder.get_object('togglebutton1').set_sensitive(1)
            self.waiting = 0
            print "salope"
        self.dictio['statusbar1'].push(self.context, '')
        self.combo3.show()
        self.throbber.hide()
        if self.origin == 'blip':
            self.builder.get_object('button4').set_label('Download')
        self.dictio['entry1'].set_sensitive(1)
        self.builder.get_object('label6').show() 

    def _chooseMode(self):
        downloader = DownloaderUI(self.app, self.app.gui.sourcelist)
        if self.app.current.uri and self.toggled:
            dest = self.app.current.uri
            dest = dest.rsplit("/", 1)[0]
            dest = dest[7:]
 
            self.video_title = self.link.rsplit("/", 1)[1]
            dest = (dest + "/" + self.video_title)
            self.preview = 0
            self.downloading = 1
            downloader.download(self.link, dest, self)
        else:
            downloader._createFileChooser(self.link, self)

    def _preview(self, bogus = None):
        ref = self.preview_reference[0][0]
        if self.origin == 'archive':
            feed = self.thumburis[self.preview_reference[0][0]][1]
            links = self.querier.getLinks(feed)
            if links == None:
                self.dictio['statusbar1'].push(self.context, _('Oops! No links were found for your media.'))
                return
            else :
                link = links[0][0]
            self.template = "".join("http://www.archive.org" + link)

        if self.origin == 'blip' and len(self.preview_reference):
            info = self.thumburis[self.preview_reference[0][0]][2]
            filename = self.blipquerier.getVideoUrl(info)
            if filename is None :
                return
            self.template =''.join('http://blip.tv/file/get/' + filename + '?referrer=blip.tv&source=1&use_direct=1&use_documents=1')
        self.viewer.play(self.template)

    def _downloadSelected(self):
        if self.origin == 'blip':
            self.format = 1
        if not self.format :
            feed = self.thumburis[self.preview_reference[0][0]][1]
            ref = self.preview_reference[0][0]
            links = self.querier.getLinks(feed)
            if links == None :
                self.format = 0
                return
            self.archiveLinkList = []
            self.dictio["button4"].set_label('Download')
            self.combo2 = gtk.combo_box_new_text()
            self.builder.get_object('vbox4').pack_end(self.combo2, expand = False)
            self.combo2.show()
            for link in links[0] :
                self.archiveLinkList.append(link)
                self.combo2.append_text(link[len(link) - 15:])
            self.combo2.set_active(0)
            self.format = 1
            return
        if self.origin == 'archive':
            self.link = "".join("http://www.archive.org" + self.archiveLinkList[self.combo2.get_active()])
            self._chooseMode()
        if self.origin == 'blip' and len(self.preview_reference):
            self.link = self.resultlist[self.preview_reference[0][0]]
            self.link = self.thumburis[self.preview_reference[0][0]][2]
            filename = self.blipquerier.getVideoUrl(self.link)
            if filename == None :
                self.dictio['statusbar1'].push(self.context, _('Oops! No links were found for your media.'))
            self.link =''.join('http://blip.tv/file/get/' + filename + '?referrer=blip.tv&source=1&use_direct=1&use_documents=1')
            self._chooseMode()
    def changeVideo(self, ref):
        if self.origin == 'blip':
            info = self.resultlist[ref]
            info = self.thumburis[ref][2]
            if not info:
                self.viewer.nextClip()
                return
            filename = self.blipquerier.getVideoUrl(info)
            if filename != None:
                self.template =''.join('http://blip.tv/file/get/' + filename + '?referrer=blip.tv&source=1&use_direct=1&use_documents=1')
            else :
                self.viewer.nextClip()
                return
            return self.template
        if ref < len(self.thumburis):
            feed = self.thumburis[ref][1]
        else :
            self.viewer.ref = 0
            self.viewer.nextClip()
            return
        links = self.querier.getLinks(feed)
        if links == None:
            self.viewer.nextClip()
            return
        link = links[0][0]
        self.template = "".join("http://www.archive.org" + link)
        return self.template

    def _destroy(self):
        self.dictio['window1'].destroy()
        return False

    def _deleteText(self):
        self.dictio['statusbar1'].push(self.context, "")

    def _notePageChangedCb(self, notebook, unused_page, page_num):
        if page_num == 1:
            self.builder.get_object('image1').hide()
        elif not self._packed:
            self.builder.get_object('image1').show()

    def _continuousSearchCb(self, button):
        self._continuousSearch(button)

    def _searchEntryCb(self, entry1):
        self.builder.get_object('togglebutton1').set_active(True)

    def _deleteTextCb(self, entry1, unused_event) :
        if self._userquery:
            if entry1.get_text() == self._userquery:
                self.builder.get_object('togglebutton1').set_label('Go !')
                entry1.set_text("")
                self.builder.get_object('togglebutton1').set_sensitive(1)

    def _saveInProjectFolderCb(self, unused_radiobutton):
        if self.toggled == 0:
            self.toggled = 1
        else :
            self.toggled = 0

    def _changeCb(self, ref):
        self.changeVideo(ref)

    def _downloadSelectedCb(self, unused_button):
        self._downloadSelected()

    def _blipTermsCb(self, unused_button):
        if self.settings.blipTerms == TERMS_NOT_ACCEPTED and self.combo3.get_active() == 1:
            self.combo3.set_active(0)
            accepter = TermsAcceptance(self.app, self, 'blip')

    def _itemActivatedCb (self, data, data2):
        _reference = data2[0]
        self.builder.get_object('label2').set_text("Loading video")
        thread.start_new_thread(self._preview, (None,))

    def _selectionChangedCb(self, iconview):
        self.format = 0
        self.preview_reference = iconview.get_selected_items()
        print self.preview_reference
        if self.origin == 'blip' and self.preview_reference != []:
            infos = self.thumburis[self.preview_reference[0][0]]
            self.builder.get_object('label1').set_text(infos[3])
            self.builder.get_object('label3').set_text("Title : " + infos[1][:20])
        if self.origin == 'archive' and self.preview_reference != []:
            infos = self.thumburis[self.preview_reference[0][0]]
            self.builder.get_object('label3').set_text("Title : " + infos[2][:20])
            self.builder.get_object('label1').set_text('')
        if self.origin == 'archive':
            self.dictio["button4"].set_label('Choose a format')
        else:
            self.dictio["button4"].set_label('Download')
        if len(self.preview_reference):
            self.shown = 1
        else:
            self.shown = 0

        if self.shown == 1:
            self.dictio["button4"].set_sensitive(1)
        elif self.shown == 0:
            self.dictio["button4"].set_sensitive(0)
        if self.combo2:
            self.combo2.destroy()
        self.viewer.viewer.playpause_button.set_sensitive(True)

    def _quit(self):
        self.lock.acquire()
        self.viewer.player.set_state(STATE_NULL)
        self.viewer.viewer.destroy()
        self.up = 0
        self.app.gui.sourcelist.importerUp = 0
        self.nothingcnt = 50
        self.stopSearch = 1
        if self.previewer :
            self.viewer.window.destroy()
        try:
            self.downloader.canc.cancel()
            if self.downloader.current != self.downloader.total :
                os.remove(self.uri)
        except:
            pass
        #FIXME : This to make sure that threads called with start_new_thread come to a term
        if self.searching:
            gobject.timeout_add(2000, self._destroy)
            self.dictio['statusbar1'].push(self.context, _('Terminating threads..'))
        else:
            self.dictio["window1"].destroy()
        self.lock.release()

    def _cancelButtonCb(self, unused_button):
        self._quit()

    def _quitImporterCb(self, unused_data, unused_button):
        self._quit()
        return True

class DownloaderUI:
    def __init__(self, app, container):
        self.app = app
        self.container = container

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
        self.builder.get_object("filechooserdialog1").set_icon_from_file("".join(instance.pixdir +
            "prometheusflame.png"))
        self.builder.get_object('filechooserdialog1').set_transient_for(instance
            .dictio['window1'])

    def download(self, url, uri, instance = None):
        self.instance.downloading += 1
        v = self.instance.builder.get_object('vbox3')
        self.video_title = url.rsplit("/", 1)[1]
        self.url = url
        self.uri = uri
        self.downloader = MultiDownloader()
        print url, uri
        self.downloader.download(url, uri)
        self.downloader.connect("finished", self._downloadFileCompleteCb)
        self.downloader.connect("progress", self._progressCb)
        self._createProgressBar()

    def _createProgressBar(self):
        # Keep a time reference for the progress bar
        self.video_title = self.video_title.split('?')[0]
        self.video_title = self.video_title[len(self.video_title) - 30:]
        self.timestarted = time.time()
        self._progressBar = gtk.ProgressBar()
        self.previous_current = 0
        self.previous_timediff = 0
        self.count = 0
        self._cancelButton = gtk.ToolButton(gtk.STOCK_CANCEL)
        self._cancelButton.show()
        self._cancelButton.connect('clicked', self._cancelButtonCb)
        self.hbox = gtk.HBox()
        self.hbox.pack_start(self._progressBar, expand = True, fill = True)
        self.hbox.pack_start(self._cancelButton, expand = False, fill = False)
        self.container.pack_start(self.hbox, expand = False, fill = True)
        self.hbox.set_spacing(6)
        self.hbox.show()
        self.hbox.show_all()

    def _quitFileChooserCb(self, unused_button):
        self.builder.get_object('filechooserdialog1').destroy()

    def _downloadFileCb(self, unused_button):
        dest = self.builder.get_object('filechooserdialog1').get_filename()
        if self.video_title is not None :
            dest = (dest + "/" + self.video_title)
        else :
            self.builder.get_object('filechooserdialog1').destroy()
            return
        self.dest = dest
        self.builder.get_object('filechooserdialog1').destroy()
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
            remaining_time = (total-current) * (timediff / current)
            text = beautify_length(int(remaining_time * SECOND))
            self._progressBar.set_text("%s left of %s at %d Kbps" % (text, self.video_title[:7], speed / 1000))

        if self.count == 1000:
            self.previous_current = current
            self.previous_timediff = timediff
            self.count = 0
        self.count += 1

    def _downloadFileCompleteCb(self, data):
        self.instance.downloading -= 1
        v = self.instance.builder.get_object('vbox3')
        if self.downloader.current == self.downloader.total :
            uri = "file://" + self.uri
            self.uri = uri[7:]
            uri = [uri]
            try:
                self.app.current.sources.addUris(uri)
            except SourceListError as error:
                pass
        self.hbox.destroy()

    def _cancelButtonCb(self, unused_button):
        self.downloader.canc.cancel()
        if self.downloader.current != self.downloader.total :
            os.remove(self.dest)
