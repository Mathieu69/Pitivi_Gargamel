import pygst
pygst.require("0.10")
import gst
import gtk
import thread
import gobject
from pitivi.ui.viewer import SimpleViewer
class Preview:

    def __init__(self, uri, instance, ref, app):
        self.undock_action = app.undock_action
        self.viewer = SimpleViewer(app, undock_action=self.undock_action)
        self.playing = 0
        self.uri = uri
        self.instance = instance
        self.ref = ref
        vbox = instance.builder.get_object('vbox3')
        align = instance.builder.get_object('alignment1')
        self.vbox = instance.builder.get_object('vbox3')
        self.vbox.pack_start(self.viewer)
        align.add(self.vbox)
        align.show_all()

        self.player = gst.element_factory_make("playbin2", "player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        self.viewer.external.do_realize()
        self.xid = self.viewer.external.window.xid

    def play(self, uri):
        print uri
        self.player.set_state(gst.STATE_NULL)
        self.player.set_property("uri", uri)
        self.playing = 1
        self.viewer.setPipeline(self.player)
        self.viewer.playing = True
        self.player.set_state(gst.STATE_PLAYING)
        self.viewer.playpause_button.setPause()
        self.instance.builder.get_object('label2').set_text("")

    def _startStopCb(self, w):
        if self.playing == 0:
            self.button.set_stock_id('gtk-media-pause')
            self.player.set_state(gst.STATE_PLAYING)
            self.playing = 1
        else:
            self.button.set_stock_id('gtk-media-play')
            self.player.set_state(gst.STATE_PAUSED)
            self.playing = 0

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)

        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()

    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            imagesink = message.src
            self.sink = imagesink
            self._switch_output_window()

    def _switch_output_window(self):
        gtk.gdk.threads_enter()
        self.sink.set_xwindow_id(self.viewer.target.window_xid)
        self.sink.expose()
        gtk.gdk.threads_leave()

    def nextClip(self):
        self.ref += 1
        print self.ref
        print 'right'
        if self.ref < len(self.instance.thumburis):
            self.player.set_state(gst.STATE_NULL)
            if self.instance.changeVideo(self.ref) is not None:
                print self.instance.changeVideo(self.ref)
                self.player.set_property("uri", self.instance.changeVideo(self.ref))
                self.button.set_image((gtk.image_new_from_stock('gtk-media-pause', gtk.ICON_SIZE_BUTTON)))
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
                self.button.set_image((gtk.image_new_from_stock('gtk-media-pause', gtk.ICON_SIZE_BUTTON)))
                self.player.set_property("uri", self.instance.changeVideo(self.ref))
                self.player.set_state(gst.STATE_PLAYING)

    def _playAnew(self):
        if self.previous == 1:
            self.ref = len(self.instance.thumburis)-1
            self.previous = 0
        self.player.set_property("uri", self.instance.changeVideo(self.ref))
        self.player.set_state(gst.STATE_PLAYING)
