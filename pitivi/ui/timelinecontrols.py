import gtk
import gobject
from pitivi.receiver import receiver, handler
import pitivi.stream as stream
from gettext import gettext as _
from common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED, LAYER_SPACING

TRACK_CONTROL_WIDTH = 75


def track_name(track):
    if track.get_caps().to_string() == "audio/x-raw-int; audio/x-raw-float":
        track_name = _("Audio:")
    else:
        track_name = _("Video:")
    return "<b>%s</b>" % track_name


class TrackControls(gtk.Label):
    __gtype_name__ = 'TrackControls'

    def __init__(self, track):
        gtk.Label.__init__(self)
        self.set_alignment(0.5, 0.1)
        self.set_markup(track_name(track))
        self.track = track
        self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_EXPANDED)

    def _setTrack(self):
        if self.track:
            self._maxPriorityChanged(None, self.track.max_priority)


class TimelineControls(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        self._tracks = []
        self.set_spacing(LAYER_SPACING)
        self.set_size_request(TRACK_CONTROL_WIDTH, -1)

## Timeline callbacks

    def _set_timeline(self):
        while self._tracks:
            self._trackRemoved(None, 0)
        if self.timeline:
            for track in self.timeline.get_tracks():
                self._trackAdded(None, track)

    timeline = receiver(_set_timeline)

    @handler(timeline, "track-added")
    def _trackAdded(self, timeline, track):
        track = TrackControls(track)
        self._tracks.append(track)
        self.pack_start(track, False, False)
        track.show()

    @handler(timeline, "track-removed")
    def _trackRemoved(self, unused_timeline, position):
        track = self._tracks[position]
        del self._tracks[position]
        self.remove(track)
