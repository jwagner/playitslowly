#!/usr/bin/env python
try:
    from psyco import proxy as optimized
except ImportError:
    optimized = lambda f: f

import math
import sys

import gobject
gobject.threads_init()

import pygst
pygst.require('0.10')

argv = sys.argv
sys.argv = []
import gst
sys.argv = argv

import struct

@gobject.type_register
class MetronomeSource(gst.BaseSrc):
    rate = 8000.0
    sample_width = 4

    __gsttemplates__ = (
        gst.PadTemplate("src",
                        gst.PAD_SRC,
                        gst.PAD_ALWAYS,
                        gst.caps_from_string("audio/x-raw-int,rate=%i,channels=1" % rate)),
        )

    bpm = 60.0
    freq = 440.0
    duration = 0.11
    volume = 2**30
    offset = 0.0

    def __init__(self, name="metronome", beep=None):
        self.__gobject_init__()
        self.curoffset = 0
        self.set_name(name)

    def set_property(self, name, value):
        setattr(self, name, value)

    def get_property(self, name):
        return getattr(self, name)

    @optimized
    def do_create(self, offset, size):
        period = self.rate/self.freq
        x = math.pi*2/period
        samples = size / self.sample_width
        samples_offset = int(offset / self.sample_width + self.offset * self.rate)
        time_offset = samples_offset/self.rate
        beat_period = self.rate/(self.bpm/60.0)
        duration = self.duration*self.rate
        data = [
                math.sin(t*x)*(t%beat_period < duration) * self.volume
                for t
                in xrange(samples_offset, samples_offset+samples)
        ]
        data = struct.pack("i"*samples, *data)
        return gst.FLOW_OK, gst.Buffer(data)


def main(argv):
    try:
        bpm = int(argv[1])
    except IndexError:
        bpm = 120
    pipeline = gst.Pipeline('filesource')
    metronome = MetronomeSource()
    metronome.set_property("bpm", bpm)
    converter = gst.element_factory_make("audioconvert")
    sink = gst.element_factory_make("autoaudiosink")

    pipeline.add(metronome, converter, sink)
    gst.element_link_many(metronome, converter, sink)
    mainloop = gobject.MainLoop()
    pipeline.set_state(gst.STATE_PLAYING)
    mainloop.run()


if __name__ == "__main__":
    main(sys.argv)
