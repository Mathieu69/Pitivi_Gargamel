import pygst
pygst.require("0.10")
import gst
import gtk
import thread
import gobject
class Preview:

    def __init__(self, uri, instance, ref):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_default_size(800, 600)
        self.playing = 1

        window.set_urgency_hint(True)
        self.window = window
        window.set_title("Video-Player")
        self.uri = uri
        self.instance = instance
        self.ref = ref
        window.connect("destroy", self._quitCb)
        vbox = gtk.VBox()
        window.add(vbox)
        hbox = gtk.HBox()

        vbox.pack_end(hbox, False)
        self.button = gtk.Button()
        self.button.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
        self.button2 = gtk.Button()
        self.button2.connect("clicked", self._quitCb)
        self.button2.set_image(gtk.image_new_from_stock(gtk.STOCK_CANCEL, gtk.ICON_SIZE_BUTTON))
        self.button3 = gtk.Button()
        self.button3.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_BUTTON))
        self.button3.connect('clicked', self._nextClipCb)
        self.button4 = gtk.Button()
        self.button4.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_BUTTON))
        self.button4.connect('clicked', self._previousClipCb)

        buttonbox = gtk.HButtonBox()
        buttonbox.pack_end(self.button2)
        buttonbox.pack_end(self.button)
        buttonbox.pack_end(self.button4)
        buttonbox.pack_end(self.button3)

        hbox.pack_start(buttonbox, False)
        self.button.connect("clicked", self.start_stop)
        self.movie_window = gtk.DrawingArea()
        vbox.add(self.movie_window)
        self.vbox = vbox
        window.show_all()

        self.player = gst.element_factory_make("playbin2", "player")
        self.xid = self.movie_window.window.xid
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        self.player.set_property("uri", self.uri)
        self.player.set_state(gst.STATE_PLAYING)

    def start_stop(self, w):
        if self.playing == 0:
            self.button.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON))
            self.player.set_state(gst.STATE_PLAYING)
            self.playing = 1
        else:
            self.player.set_state(gst.STATE_PAUSED)
            self.button.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON))
            self.playing = 0

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.ref += 1
            self._nextClipCb('blip')

        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            self.button.set_label("Start")

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            imagesink = message.src
            imagesink.set_property("force-aspect-ratio", True)
            imagesink.set_xwindow_id(self.xid)

    def _quitCb(self, unused_button):
        self.player.set_state(gst.STATE_NULL)
        self.instance.previewer = 0
        self.window.destroy()

    def _nextClipCb(self, unused_button):
        self.ref += 1
        if self.ref < len(self.instance.thumburis):
            self.player.set_state(gst.STATE_NULL)
            self.player.set_property("uri", self.instance._changeCb(self.ref))
            self.player.set_state(gst.STATE_PLAYING)
        elif self.instance.origin == 'archive':
            self.player.set_state(gst.STATE_NULL)
            self.ref = 0
            self.instance.combo.set_active(self.instance.page + 1)
            gobject.timeout_add(15000, self._playAnew)

    def _previousClipCb(self, unused_button):
        if self.ref > 0 :
            self.ref -= 1
            self.player.set_state(gst.STATE_NULL)
            print self.ref, len(self.instance.thumburis)
            self.player.set_property("uri", self.instance._changeCb(self.ref))
            self.player.set_state(gst.STATE_PLAYING)
        elif self.instance.page > 1  and self.instance.origin == 'archive':
            self.player.set_state(gst.STATE_NULL)
            self.instance.combo.set_active(self.instance.page - 1)
            self.ref = len(self.instance.thumburis)-1
            gobject.timeout_add(15000, self._playAnew)

    def _playAnew(self):
        self.player.set_property("uri", self.instance._changeCb(self.ref))
        self.player.set_state(gst.STATE_PLAYING)
