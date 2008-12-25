#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
import sys

import gobject
gobject.threads_init()

import pygst
pygst.require('0.10')
import gst

import pygtk
pygtk.require('2.0')
import gtk

import mygtk

_ = lambda s: s

NAME = u"Play it slowly"
VERSION = "1.0"
WEBSITE = "http://29a.ch/"

TIME_FORMAT = gst.Format(gst.FORMAT_TIME)

class Pipeline(gst.Pipeline):
    def __init__(self):
        gst.Pipeline.__init__(self)
        self.playbin = gst.element_factory_make("playbin")
        self.add(self.playbin)

        bin = gst.Bin("speed-bin")
        self.speedchanger = gst.element_factory_make("pitch")
        bin.add(self.speedchanger)
        self.audiosink = gst.element_factory_make("autoaudiosink")
        bin.add(self.audiosink)
        gst.element_link_many(self.speedchanger, self.audiosink)
        sink_pad = gst.GhostPad("sink", self.speedchanger.get_pad("sink"))
        bin.add_pad(sink_pad)
        self.playbin.set_property("audio-sink", bin)
        bus = self.playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        self.eos = lambda: None

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.eos()
        elif t == gst.MESSAGE_ERROR:
            mygtk.show_error("gstreamer error: %s - %s" % message.parse_error())

    def set_volume(self, volume):
        self.playbin.set_property("volume", volume)

    def set_speed(self, speed):
        self.speedchanger.set_property("tempo", speed)

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

        bus = playbin.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        pipeline.set_state(gst.STATE_PLAYING)

        return (pipeline, playbin)

    def set_file(self, uri):
        self.playbin.set_property("uri", uri)

    def play(self):
        self.set_state(gst.STATE_PLAYING)

    def pause(self):
        self.set_state(gst.STATE_READY)

class MainWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self,gtk.WINDOW_TOPLEVEL)

        self.set_title(NAME)
        try:
            self.set_icon(mygtk.iconfactory.get_icon("playitslowly", 128))
        except gobject.GError:
            print "could not load playitslowly icon"
        self.set_default_size(440, 200)
        self.set_border_width(5)

        self.vbox = gtk.VBox()

        self.pipeline = Pipeline()

        filedialog = mygtk.FileChooserDialog(gtk.FILE_CHOOSER_ACTION_OPEN, parent=self)
        filedialog.connect("response", self.filechanged)
        self.filechooser = gtk.FileChooserButton(filedialog)

        self.speedchooser = gtk.HScale(gtk.Adjustment(1.0, 0.1, 2.0))
        self.speedchooser.set_value_pos(gtk.POS_LEFT)
        self.speedchooser.connect("value-changed", self.speedchanged)

        self.pitchchooser = gtk.HScale(gtk.Adjustment(1.0, 0.1, 4.0))
        self.pitchchooser.set_value_pos(gtk.POS_LEFT)
        self.pitchchooser.connect("value-changed", self.pitchchanged)

        self.positionchooser = gtk.HScale(gtk.Adjustment(0, 0, 0))
        self.positionchooser.set_value_pos(gtk.POS_LEFT)
        self.positionchooser.connect("button-press-event", self.start_seeking)
        self.positionchooser.connect("button-release-event", self.positionchanged)
        self.seeking = False

        self.startchooser = gtk.HScale(gtk.Adjustment(0, 0, 0))
        self.startchooser.set_value_pos(gtk.POS_LEFT)
        self.startchooser.connect("button-press-event", self.start_seeking)
        self.startchooser.connect("button-release-event", self.seeked)
        self.endchooser = gtk.HScale(gtk.Adjustment(1, 0, 1))
        self.endchooser.set_value_pos(gtk.POS_LEFT)
        self.endchooser.connect("button-press-event", self.start_seeking)
        self.endchooser.connect("button-release-event", self.seeked)

        self.vbox.pack_start(mygtk.form([
            (_(u"Audio File:"), self.filechooser),
            (_(u"Playback speed:"), self.speedchooser),
            (_(u"Playback Pitch:"), self.pitchchooser),
            (_(u"Current Position:"), self.positionchooser),
            (_(u"Start Position:"), self.startchooser),
            (_(u"End Position:"), self.endchooser)
        ]), False, False)

        buttonbox = gtk.HButtonBox()
        self.vbox.pack_end(buttonbox, False, False)

        self.play_button = gtk.ToggleButton(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("toggled", self.play)
        self.play_button.set_use_stock(True)
        self.play_button.set_sensitive(False)
        buttonbox.pack_start(self.play_button)

        self.volume_button = gtk.VolumeButton()
        self.volume_button.set_value(1.0)
        self.volume_button.set_relief(gtk.RELIEF_NORMAL)
        self.volume_button.connect("value-changed", self.volumechanged)
        buttonbox.pack_start(self.volume_button)

        self.save_as_button = gtk.Button(stock=gtk.STOCK_SAVE_AS)
        self.save_as_button.connect("clicked", self.save)
        self.save_as_button.set_sensitive(False)
        buttonbox.pack_start(self.save_as_button)

        button_about = gtk.Button(stock=gtk.STOCK_ABOUT)
        button_about.connect("clicked", self.about)
        buttonbox.pack_end(button_about)

        self.add(self.vbox)
        self.connect("destroy", gtk.main_quit)

    def volumechanged(self, sender, foo):
        self.pipeline.set_volume(sender.get_value())

    def save(self, sender):
        dialog = mygtk.FileChooserDialog(gtk.FILE_CHOOSER_ACTION_SAVE,
                u"Save modified version as", self)
        dialog.set_current_name("export.wav")
        if dialog.run() == gtk.RESPONSE_OK:
            self.pipeline.set_file(self.filechooser.get_uri())
            self.foo = self.pipeline.save_file(dialog.get_filename())
        dialog.destroy()

    def filechanged(self, sender, response_id):
        self.play_button.set_sensitive(True)
        self.save_as_button.set_sensitive(True)
        if response_id == gtk.RESPONSE_OK:
            self.play_button.set_active(False)

    def pipe_time(self, t):
        return t/self.speedchooser.get_value()*1000000000

    def song_time(self, t):
        return t*self.speedchooser.get_value()/1000000000

    def start_seeking(self, sender, foo):
        self.seeking = True

    def seeked(self, sender, foo):
        self.seeking = False

    def positionchanged(self, sender, foo):
        self.seek(sender.get_value())
        self.seeking = False

    def seek(self, pos):
        pos = self.pipe_time(pos)
        self.pipeline.playbin.seek_simple(TIME_FORMAT, gst.SEEK_FLAG_FLUSH, pos)

    def speedchanged(self, sender):
        self.pipeline.set_speed(sender.get_value())

    def pitchchanged(self, sender):
        self.pipeline.set_pitch(sender.get_value())

    def play(self, sender):
        if sender.get_active():
            self.pipeline.set_file(self.filechooser.get_uri())
            self.pipeline.play()
            gobject.timeout_add(900, self.update_position)
        else:
            self.pipeline.pause()

    def update_position(self):
        if self.seeking:
            return self.play_button.get_active()
        position, fmt = self.pipeline.playbin.query_position(TIME_FORMAT, None)
        duration, fmt = self.pipeline.playbin.query_duration(TIME_FORMAT, None)
        position = self.song_time(position)
        duration = self.song_time(duration)
        start = self.startchooser.get_value()
        end = self.endchooser.get_value()

        if end < start:
            # stupid user...
            self.play_button.set_active(False)
            return False

        if position > end or position < start:
            self.seek(start)
            return True

        self.positionchooser.set_range(0, duration)
        end = self.endchooser.get_adjustment()
        delta = end.value-end.upper
        self.startchooser.set_range(0, duration)
        self.endchooser.set_range(0, duration)
        self.endchooser.set_value(duration+delta)
        self.positionchooser.set_value(position)
        return self.play_button.get_active()

    def about(self, sender):
        """show an about dialog"""
        about = gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_logo(mygtk.iconfactory.get_icon("playitslowly", 128))
        about.set_name(NAME)
        about.set_version(VERSION)
#        about.set_comments("")
        about.set_authors(["Jonas Wagner"])
        about.set_translator_credits(_("translator-credits"))
        about.set_copyright("Copyright (c) 2008 Jonas Wagner")
        about.set_website(WEBSITE)
        about.set_website_label(WEBSITE)
        about.set_license("""
Copyright (C) 2008 Jonas Wagner
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
""")
        about.run()
        about.destroy()

def main():
    MainWindow().show_all()
    gtk.main()

if __name__ == "__main__":
    main()
