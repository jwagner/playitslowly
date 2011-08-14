#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
from __future__ import with_statement
"""
Author: Andrzej Bieniek

Play it slowly console application
Copyright (C) 2011 Andrzej Bieniek

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

import os, sys, time, thread
import glib, gobject
from optparse import OptionParser
from datetime import timedelta
from playitslowly.pipeline import Pipeline
import gst


class AppCli:
    def __init__(self, filepath, outfilepath, speed):
        self.filepath = filepath
        self.outfilepath = outfilepath
        self.speed = speed
        self.duration = None
        self.close = False

    def set_loop(self, loop):
        self.loop = loop

    def on_eos(self):
        self.close = True

    def read_duration(self, pipeline):
        try:
            duration_seconds = pipeline.query_duration(gst.FORMAT_TIME)[0]/1000000000
            duration = timedelta(seconds=duration_seconds)
        except:
            return None
        else:
            return duration

    def read_position(self, pipeline):
        try:
            position_seconds = pipeline.query_position(gst.FORMAT_TIME)[0]/1000000000
            position = timedelta(seconds=position_seconds)
        except:
            return None
        else:
            return position

    def save_file_thread(self):
        sink = gst.parse_bin_from_description("fakesink", True)
        pipeline = Pipeline(sink)
        pipeline.reset()
        pipeline.set_file('file://' + self.filepath)
        pipeline.set_speed(self.speed)
        pipeline.set_on_eos_cb(self.on_eos)
        a,b = pipeline.save_file(self.outfilepath)
        self.pipeline_save = a
        while not self.close:
            if not self.duration:
                d = self.read_duration(self.pipeline_save)
                if d:
                    self.duration = d
                    input_duration = timedelta(seconds = d.total_seconds() * self.speed)
                    print 'Original file duration: %s' %input_duration
            position = self.read_position(self.pipeline_save)
            if position:
                if self.duration:
                    print 'Position: %s/%s %s[%%]' %(position, self.duration, int(position.total_seconds()*100//self.duration.total_seconds()))
                else:
                    print 'Position: %s/-' %position
            time.sleep(1)
        print 'Done'
        self.pipeline_save.set_state(gst.STATE_NULL)
        self.loop.quit()


def main():
    desc = 'Application changes playback speed and sotres converted file in a wav format. \
            Suffix with speed information is added to the wav file.'
    parser = OptionParser('playitslowlycli [options] audiofile', description=desc)
    parser.add_option("-s", "--speed", dest="speed",
                  help="playback speed, (value 1 means unchanged)")

    (options, args) = parser.parse_args(sys.argv[1:])
    if options.speed:
        speed = float(options.speed)
    else:
        speed = 1.3

    file_not_found = True
    arg_file = ''
    if len(args) == 1:
        arg_file = args[0]
        filepath = os.path.abspath(args[0])
        if os.path.exists(args[0]):
            file_not_found = False
    if file_not_found:
        print 'Error: file \'%s\' not found.' %arg_file
        parser.print_help()
        sys.exit(-1)

    outfilepath = os.path.splitext(os.path.split(filepath)[1])[0] + '_s%s.wav' %speed
    print 'Speed: %s, %s -> %s' %(speed, arg_file, outfilepath)
    loop = glib.MainLoop()

    client = AppCli(filepath,outfilepath, speed)
    client.set_loop(loop)
    thread.start_new_thread(client.save_file_thread, ())
    gobject.threads_init()
    loop.run()


if __name__ == "__main__":
    main()
