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

class Pipeline2(Gst.Pipeline):
    def __init__(self, sink):
        Gst.Pipeline.__init__(self)
        self.playbin = Gst.ElementFactory.make("playbin")
        self.add(self.playbin)

        self.speedchanger = Gst.ElementFactory.make("pitch")
        if self.speedchanger is None:
            myGtk.show_error(_(u"You need to install the Gstreamer soundtouch elements for "
                    "play it slowly to. They are part of Gstreamer-plugins-bad. Consult the "
                    "README if you need more information.")).run()
            raise SystemExit()
        self.add(self.speedchanger)

        self.audiosink = sink
        self.add(self.audiosink)

        convert = Gst.ElementFactory.make("audioconvert")
        self.add(convert)

        #self.playbin.link(convert)
        self.speedchanger.link(convert)

        self.playbin.set_property('audio-sink', self.audiosink)
        convert.link(self.audiosink)

        bus = self.get_bus()
        # TODO: crashes
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.eos = lambda: None

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.eos()
        elif t == Gst.MessageType.ERROR:
            print message
            print message.parse_error()
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
        #playbin.set_property("uri", self.playbin.get_property("uri"))

        speedchanger = Gst.ElementFactory.make("pitch")
        speedchanger.set_property("tempo", self.speedchanger.get_property("tempo"))
        speedchanger.set_property("pitch", self.speedchanger.get_property("pitch"))
        pipeline.add(speedchanger)

        audioconvert = Gst.ElementFactory.make("audioconvert")
        pipeline.add(audioconvert)

        encoder = Gst.ElementFactory.make("wavenc")
        pipeline.add(encoder)

        filesink = Gst.ElementFactory.make("filesink")
        pipeline.add(filesink)
        filesink.set_property("location", uri)

        Gst.element_link_many(speedchanger, audioconvert)
        Gst.element_link_many(audioconvert, encoder)
        Gst.element_link_many(encoder, filesink)

        #sink_pad = Gst.GhostPad.new("sink", speedchanger.get_static_pad("sink"))
        #pipeline.add_pad(sink_pad)
        playbin.set_property("audio-sink", bin)

        bus = playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        pipeline.set_state(Gst.State.PLAYING)

        return (pipeline, playbin)

    def set_file(self, uri):
        print "set_file", uri
        self.playbin.set_property("uri", uri)

    def play(self):
        print "set_state PLAYING"
        self.set_state(Gst.State.PLAYING)

    def pause(self):
        self.set_state(Gst.State.PAUSED)

    def reset(self):
        self.set_state(Gst.State.READY)



class Pipeline(object):
    def __init__(self, sink):
        self.playbin = Gst.ElementFactory.make("playbin", "player")
        #self.add(self.playbin)

        #self.audiosink = Gst.ElementFactory.make('pulsesink')
        #self.fakesink = Gst.ElementFactory.make('fakesink')
        #self.add(self.audiosink)
        #self.playbin.set_property('video-sink', self.fakesink)
        #self.playbin.set_property('audio-sink', self.audiosink)
        #self.playbin.set_property('audio-sink', self.fakesink)
        bus = self.playbin.get_bus()
        # TODO: crashes
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.eos = lambda: None

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.eos()
        elif t == Gst.MessageType.ERROR:
            print message
            print message.parse_error()
            myGtk.show_error("Gstreamer error: %s - %s" % message.parse_error())

    def set_volume(self, volume):
        self.playbin.set_property("volume", volume)

    def set_speed(self, speed):
        return
        self.speedchanger.set_property("tempo", speed)

    def get_speed(self):
        return
        return self.speedchanger.get_property("tempo")

    def pipe_time(self, t):
        """convert from song position to pipeline time"""
        return
        return t/self.get_speed()*1000000000

    def song_time(self, t):
        """convert from pipetime time to song position"""
        return
        return t*self.get_speed()/1000000000

    def set_pitch(self, pitch):
        return
        self.speedchanger.set_property("pitch", pitch)

    def save_file(self, uri):
        return
        pipeline = Gst.Pipeline()

        playbin = Gst.ElementFactory.make("playbin")
        pipeline.add(playbin)
        #playbin.set_property("uri", self.playbin.get_property("uri"))

        speedchanger = Gst.ElementFactory.make("pitch")
        speedchanger.set_property("tempo", self.speedchanger.get_property("tempo"))
        speedchanger.set_property("pitch", self.speedchanger.get_property("pitch"))
        pipeline.add(speedchanger)

        audioconvert = Gst.ElementFactory.make("audioconvert")
        pipeline.add(audioconvert)

        encoder = Gst.ElementFactory.make("wavenc")
        pipeline.add(encoder)

        filesink = Gst.ElementFactory.make("filesink")
        pipeline.add(filesink)
        filesink.set_property("location", uri)

        Gst.element_link_many(speedchanger, audioconvert)
        Gst.element_link_many(audioconvert, encoder)
        Gst.element_link_many(encoder, filesink)

        #sink_pad = Gst.GhostPad.new("sink", speedchanger.get_static_pad("sink"))
        #pipeline.add_pad(sink_pad)
        playbin.set_property("audio-sink", bin)

        bus = playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        pipeline.set_state(Gst.State.PLAYING)

        return (pipeline, playbin)

    def set_file(self, uri):
        print "set_file", uri
        self.playbin.set_property("uri", uri)

    def play(self):
        print "set_state PLAYING"
        self.set_state(Gst.State.PLAYING)

    def pause(self):
        self.set_state(Gst.State.PAUSED)

    def reset(self):
        self.set_state(Gst.State.READY)

    def set_state(self, state):
        self.playbin.set_state(state)



