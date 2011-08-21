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
from playitslowly.pipeline import Pipeline, pipeline_encoders
import gst


class AppCli:
    def __init__(self, filepath, outfilepath, speed, sink):
        self.filepath = filepath
        self.outfilepath = outfilepath
        self.speed = speed
        self.sink = sink
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

    def prepare_pipeline(self):
        gstsink = gst.parse_bin_from_description(self.sink, True)
        self.pipeline = Pipeline(gstsink)
        self.pipeline.reset()
        self.pipeline.set_file('file://' + self.filepath)
        self.pipeline.set_speed(self.speed)
        self.pipeline.set_on_eos_cb(self.on_eos)

    def set_encoder(self, encoder):
        self.pipeline.set_encoder(encoder)
    
    def __monitor_progress(self, pipeline):
        while not self.close:
            if not self.duration:
                d = self.read_duration(pipeline)
                if d:
                    self.duration = d
                    input_duration = timedelta(seconds = d.total_seconds() * self.speed)
                    print 'Original file duration: %s' %input_duration
            position = self.read_position(pipeline)
            if position:
                if self.duration:
                    print 'Position: %s/%s %s[%%]' %(position, self.duration, int(position.total_seconds()*100//self.duration.total_seconds()))
                else:
                    print 'Position: %s/-' %position
            time.sleep(1)

            
    def save_file_thread(self):
        pipeline_save,b = self.pipeline.save_file(self.outfilepath)
        self.__monitor_progress(pipeline_save)
        print 'Done'
        pipeline_save.set_state(gst.STATE_NULL)
        self.loop.quit()

    def play_file_thread(self):
        self.pipeline.play()
        self.__monitor_progress(self.pipeline)
        print 'Done'
        self.pipeline.set_state(gst.STATE_NULL)
        self.loop.quit()


def main():
    encoders_keys_str = ''
    for key in pipeline_encoders.keys():
        encoders_keys_str += ', ' + pipeline_encoders[key].file_extension
    encoders_keys_str = encoders_keys_str[2:]   #Cut first ' ,'
    desc = '\
Application changes playback speed. By default it plays the audio track. \
When encoder is set (-e option) it sotres audio to the file. \
Suffix with speed information and codec extension is added to the output file.'
    parser = OptionParser('playitslowlycli [options] audiofile', description=desc)
    parser.add_option("--sink", dest="sink",
                  help="specify gstreamer sink for playback")
    parser.add_option("-s", "--speed", dest="speed",
                  help="playback speed, (value 1 means unchanged)")
    parser.add_option("-e", "--encoder", dest="encoder",
                  help="audio encoder (when selected audio is tored to file). Available encoders: %s" %encoders_keys_str)

    (options, args) = parser.parse_args(sys.argv[1:])
    if options.speed:
        speed = float(options.speed)
    else:
        speed = 1.3
    if options.sink:
        sink = options.sink
    else:
        sink = 'autoaudiosink'

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

    if options.encoder:
        if options.encoder not in pipeline_encoders.keys():
            print 'Error: encoder \'%s\' not found.' %options.encoder
            parser.print_help()
            sys.exit(-1)

    loop = glib.MainLoop()
    outfilepath = os.path.splitext(os.path.split(filepath)[1])[0] + '_s%s.%s' %(speed, options.encoder)
    client = AppCli(filepath, outfilepath, speed, sink)
    client.set_loop(loop)
    client.prepare_pipeline()
    if options.encoder:
        print 'Saving to file, speed: %s, %s -> %s' %(speed, arg_file, outfilepath)
        client.set_encoder( pipeline_encoders[options.encoder] )
        thread.start_new_thread(client.save_file_thread, ())
    else:
        print 'Playing, speed: %s, %s' %(speed, arg_file)
        thread.start_new_thread(client.play_file_thread, ())
    gobject.threads_init()
    loop.run()


if __name__ == "__main__":
    main()
