import pygst
pygst.require("0.10")
import gst
import gtk
import thread
import gobject
class Preview:

    def __init__(self, uri, instance, ref):
        self.playing = 0
        self.uri = uri
        self.instance = instance
        self.ref = ref
        vbox = gtk.VBox()
        instance.builder.get_object('alignment1').add(vbox)
        hbox = gtk.HBox()

        vbox.pack_end(hbox, False)
        self.button = gtk.ToolButton(icon_widget = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
        self.buttonalt = gtk.ToolButton(icon_widget = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON))
        self.button2 = gtk.ToolButton(gtk.image_new_from_stock(gtk.STOCK_CANCEL, gtk.ICON_SIZE_BUTTON))
        self.button2.connect("clicked", self._quitCb)
        self.button3 = gtk.ToolButton(gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_BUTTON))
        self.button3.connect('clicked', self._nextClipCb)
        self.button4 = gtk.ToolButton(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_BUTTON))
        self.button4.connect('clicked', self._previousClipCb)

        buttonbox = gtk.HButtonBox()
        buttonbox.pack_end(self.button2)
        buttonbox.pack_end(self.button)
        buttonbox.pack_end(self.buttonalt)
        buttonbox.pack_end(self.button4)
        buttonbox.pack_end(self.button3)

        hbox.pack_start(buttonbox, False)
        self.button.connect("clicked", self._startStopCb)
        self.movie_window = gtk.DrawingArea()
        vbox.add(self.movie_window)
        self.vbox = vbox
        instance.builder.get_object('alignment1').show_all()

        self.player = gst.element_factory_make("playbin2", "player")
        self.xid = self.movie_window.window.xid
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        self.id = self.button.get_icon_widget()
        self.idalt = self.buttonalt.get_icon_widget()
        if self.uri is not None :
            self.player.set_property("uri", self.uri)
            self.player.set_state(gst.STATE_PLAYING)
            self.playing = 1
        self.buttonalt.hide()

    def _startStopCb(self, w):
        if self.playing == 0:
            self.button.stock_id = gtk.STOCK_MEDIA_PAUSE
            self.player.set_state(gst.STATE_PLAYING)
            self.button.set_icon_widget(self.id)
            self.playing = 1
        else:
            self.button.set_icon_widget(self.idalt)
            self.player.set_state(gst.STATE_PAUSED)
            self.playing = 0
        print self.id

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.nextClip()

        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_xwindow_id(self.xid)

    def nextClip(self):
        self.ref += 1
        print self.ref
        if self.ref < len(self.instance.thumburis):
            self.player.set_state(gst.STATE_NULL)
            if self.instance.changeVideo(self.ref) is not None:
                self.player.set_property("uri", self.instance.changeVideo(self.ref))
                self.player.set_state(gst.STATE_PLAYING)

    def quit(self):
        self.player.set_state(gst.STATE_NULL)
        self.instance.previewer = 0
        self.vbox.destroy()

    def _quitCb(self, unused_button):
        self.quit()

    def _nextClipCb(self, unused_button):
        self.nextClip()

    def _previousClipCb(self, unused_button):
        if self.ref > 0 :
            self.ref -= 1
            self.player.set_state(gst.STATE_NULL)
            print self.ref, len(self.instance.thumburis)
            if self.instance.changeVideo(self.ref) is not None:
                self.player.set_property("uri", self.instance.changeVideo(self.ref))
                self.player.set_state(gst.STATE_PLAYING)

    def _playAnew(self):
        if self.previous == 1:
            self.ref = len(self.instance.thumburis)-1
            self.previous = 0
        self.player.set_property("uri", self.instance.changeVideo(self.ref))
        self.player.set_state(gst.STATE_PLAYING)
