import sys

import pygst
pygst.require('0.10')

argv = sys.argv
# work around gstreamer parsing sys.argv!
sys.argv = []
import gst
sys.argv = argv

from playitslowly import mygtk

_ = lambda x: x

class Pipeline(gst.Pipeline):
    def __init__(self, sink):
        gst.Pipeline.__init__(self)
        self.playbin = gst.element_factory_make("playbin")
        self.add(self.playbin)

        bin = gst.Bin("speed-bin")
        try:
            self.speedchanger = gst.element_factory_make("pitch")
        except gst.ElementNotFoundError:
            mygtk.show_error(_(u"You need to install the gstreamer soundtouch elements for "
                    "play it slowly to. They are part of gstreamer-plugins-bad. Consult the "
                    "README if you need more information.")).run()
            raise SystemExit()

        bin.add(self.speedchanger)

        self.audiosink = sink

        bin.add(self.audiosink)
        convert = gst.element_factory_make("audioconvert")
        bin.add(convert)
        gst.element_link_many(self.speedchanger, convert)
        gst.element_link_many(convert, self.audiosink)
        sink_pad = gst.GhostPad("sink", self.speedchanger.get_pad("sink"))
        bin.add_pad(sink_pad)
        self.playbin.set_property("audio-sink", bin)
        bus = self.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.eos = lambda: None
        self.on_eos_cb = None

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.eos()
            if self.on_eos_cb:
                self.on_eos_cb()
        elif t == gst.MESSAGE_ERROR:
            mygtk.show_error("gstreamer error: %s - %s" % message.parse_error())

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
        pipeline = gst.Pipeline()

        playbin = gst.element_factory_make("playbin")
        pipeline.add(playbin)
        playbin.set_property("uri", self.playbin.get_property("uri"))

        bin = gst.Bin("speed-bin")

        speedchanger = gst.element_factory_make("pitch")
        speedchanger.set_property("tempo", self.speedchanger.get_property("tempo"))
        speedchanger.set_property("pitch", self.speedchanger.get_property("pitch"))
        bin.add(speedchanger)

        audioconvert = gst.element_factory_make("audioconvert")
        bin.add(audioconvert)

        encoder = gst.element_factory_make("wavenc")
        bin.add(encoder)

        filesink = gst.element_factory_make("filesink")
        bin.add(filesink)
        filesink.set_property("location", uri)

        gst.element_link_many(speedchanger, audioconvert)
        gst.element_link_many(audioconvert, encoder)
        gst.element_link_many(encoder, filesink)

        sink_pad = gst.GhostPad("sink", speedchanger.get_pad("sink"))
        bin.add_pad(sink_pad)
        playbin.set_property("audio-sink", bin)

        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        pipeline.set_state(gst.STATE_PLAYING)

        return (pipeline, playbin)

    def set_file(self, uri):
        self.playbin.set_property("uri", uri)

    def play(self):
        self.set_state(gst.STATE_PLAYING)

    def pause(self):
        self.set_state(gst.STATE_PAUSED)

    def reset(self):
        self.set_state(gst.STATE_READY)

    def set_on_eos_cb(self, on_eos_cb):
        self.on_eos_cb = on_eos_cb
