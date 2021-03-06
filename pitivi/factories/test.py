#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       base.py
#
# Copyright (c) 2005-2008, Edward Hervey <bilboed@bilboed.com>
#               2008, Alessandro Decina <alessandro.decina@collabora.co.uk>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gst
from pitivi.factories.base import SourceFactory
from pitivi.factories.operation import EffectFactory
from pitivi.stream import VideoStream, AudioStream

class VideoTestSourceFactory(SourceFactory):
    def __init__(self, pattern=0):
        SourceFactory.__init__(self, "videotestsrc://")
        self.pattern = pattern

        caps = gst.Caps('video/x-raw-yuv; video/x-raw-rgb')
        self.addOutputStream(VideoStream(caps))

    def _makeStreamBinReal(self, output_stream=None):
        if output_stream is None:
            output_stream = self.output_streams[0]

        bin = gst.Bin()
        videotestsrc = gst.element_factory_make('videotestsrc')
        videotestsrc.props.pattern = self.pattern
        capsfilter = gst.element_factory_make('capsfilter',
                "videotestsrc-capsfilter")
        capsfilter.props.caps = output_stream.caps.copy()

        bin.add(videotestsrc)
        bin.add(capsfilter)
        videotestsrc.link_pads_full("src", capsfilter, "sink", gst.PAD_LINK_CHECK_NOTHING)

        return bin

    def _makeStreamBin(self, output_stream):
        video_bin = SourceFactory._makeStreamBin(self, output_stream)
        capsfilter = video_bin.get_by_name("videotestsrc-capsfilter")
        queue = video_bin.get_by_name("internal-queue")
        capsfilter.link_pads_full("src", queue, "sink", gst.PAD_LINK_CHECK_NOTHING)

        capsfilter = video_bin.get_by_name("capsfilter-proj-settings")
        target = capsfilter.get_pad("src")
        ghost = gst.GhostPad('src', target)
        video_bin.add_pad(ghost)

        return video_bin

    def _makeDefaultBin(self):
        return self._makeStreamBin(self.output_streams[0])

    def _releaseBin(self, bin):
        pass

class AudioTestSourceFactory(SourceFactory):
    def __init__(self, wave=0):
        SourceFactory.__init__(self, "audiotestsrc://")
        self.wave = wave

        caps = gst.Caps('audio/x-raw-int; audio/x-raw-float')
        self.addOutputStream(AudioStream(caps))

    def _makeBin(self, output_stream=None):
        if output_stream is None:
            output_stream = self.output_streams[0]

        bin = gst.Bin()
        audiotestsrc = gst.element_factory_make('audiotestsrc', "real-audiotestsrc")
        audiotestsrc.props.wave = self.wave
        ares = gst.element_factory_make("audioresample", "default-audioresample")
        aconv = gst.element_factory_make("audioconvert", "default-audioconvert")
        capsfilter = gst.element_factory_make('capsfilter')
        capsfilter.props.caps = output_stream.caps.copy()

        bin.add(audiotestsrc, ares, aconv, capsfilter)
        audiotestsrc.link_pads_full("src", aconv, "sink", gst.PAD_LINK_CHECK_NOTHING)
        aconv.link_pads_full("src", ares, "sink", gst.PAD_LINK_CHECK_NOTHING)
        ares.link_pads_full("src", capsfilter, "sink", gst.PAD_LINK_CHECK_NOTHING)

        target = capsfilter.get_pad('src')
        ghost = gst.GhostPad('src', target)
        bin.add_pad(ghost)

        return bin

    def _releaseBin(self, bin):
        pass

    def getInterpolatedProperties(self, stream):
        props = SourceFactory.getInterpolatedProperties(self, stream)
        props.update({"volume": None})
        return props


class TestEffectFactory(EffectFactory):
    def __init__(self, stream):
        EffectFactory.__init__(self, "identity", "identity")

        caps = gst.Caps('video/x-raw-rgb')
        self.addOutputStream(stream)
        self.addInputStream(stream)
