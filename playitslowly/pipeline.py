"""
Author: Jonas Wagner

Play it Slowly
Copyright (C) 2009 - 2015 Jonas Wagner

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys

argv = sys.argv
# work around Gstreamer parsing sys.argv!
sys.argv = []

import gi
gi.require_version('Gst', '1.0')

from gi.repository import Gst
sys.argv = argv

from playitslowly import myGtk

_ = lambda x: x

class Pipeline(Gst.Pipeline):
    def __init__(self, sink):
        Gst.Pipeline.__init__(self)
        self.playbin = Gst.ElementFactory.make("playbin")
        self.add(self.playbin)

        bin = Gst.Bin()
        self.speedchanger = Gst.ElementFactory.make("pitch")
        if self.speedchanger is None:
            myGtk.show_error(_("You need to install the Gstreamer soundtouch elements for "
                    "play it slowly to. They are part of Gstreamer-plugins-bad. Consult the "
                    "README if you need more information.")).run()
            raise SystemExit()

        bin.add(self.speedchanger)

        self.audiosink = Gst.parse_launch(sink)
        #self.audiosink = Gst.ElementFactory.make(sink, "sink")

        bin.add(self.audiosink)
        convert = Gst.ElementFactory.make("audioconvert")
        bin.add(convert)
        self.speedchanger.link(convert)
        convert.link(self.audiosink)
        sink_pad = Gst.GhostPad.new("sink", self.speedchanger.get_static_pad("sink"))
        bin.add_pad(sink_pad)
        self.playbin.set_property("audio-sink", bin)
        #bus = self.playbin.get_bus()
        #bus.add_signal_watch()
        #bus.connect("message", self.on_message)

        self.eos = lambda: None

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MESSAGE_EOS:
            self.eos()
        elif t == Gst.MESSAGE_ERROR:
            myGtk.show_error("Gstreamer error: %s - %s" % message.parse_error())

    def set_volume(self, volume):
        self.playbin.set_property("volume", volume)

    def set_speed(self, speed):
        self.speedchanger.set_property("tempo", speed)

    def get_speed(self):
        return self.speedchanger.get_property("tempo")

    def pipe_time(self, t):
        """convert from song position to pipeline time"""
        return t/self.get_speed()*1000000000

    def song_time(self, t):
        """convert from pipetime time to song position"""
        return t*self.get_speed()/1000000000

    def set_pitch(self, pitch):
        self.speedchanger.set_property("pitch", pitch)

    def save_file(self, uri):
        pipeline = Gst.Pipeline()

        playbin = Gst.ElementFactory.make("playbin")
        pipeline.add(playbin)
        playbin.set_property("uri", self.playbin.get_property("uri"))

        bin = Gst.Bin()

        speedchanger = Gst.ElementFactory.make("pitch")
        speedchanger.set_property("tempo", self.speedchanger.get_property("tempo"))
        speedchanger.set_property("pitch", self.speedchanger.get_property("pitch"))
        bin.add(speedchanger)

        audioconvert = Gst.ElementFactory.make("audioconvert")
        bin.add(audioconvert)

        encoder = Gst.ElementFactory.make("wavenc")
        bin.add(encoder)

        filesink = Gst.ElementFactory.make("filesink")
        bin.add(filesink)
        filesink.set_property("location", uri)

        speedchanger.link(audioconvert)
        audioconvert.link(encoder)
        encoder.link(filesink)

        sink_pad = Gst.GhostPad.new("sink", speedchanger.get_static_pad("sink"))
        bin.add_pad(sink_pad)
        playbin.set_property("audio-sink", bin)

        pipeline.set_state(Gst.State.PLAYING)

        return (pipeline, playbin)

    def set_file(self, uri):
        self.playbin.set_property("uri", uri)

    def play(self):
        self.set_state(Gst.State.PLAYING)

    def pause(self):
        self.set_state(Gst.State.PAUSED)

    def reset(self):
        self.set_state(Gst.State.READY)


