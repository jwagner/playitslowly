#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
from __future__ import with_statement
"""
Author: Jonas Wagner

Play it slowly
Copyright (C) 2009 - 2010 Jonas Wagner

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

import getopt
import mimetypes
import os
import sys

try:
    import json
except ImportError:
    import simplejson as json

import gobject
gobject.threads_init()

import pygtk
pygtk.require('2.0')
import gtk

# always enable button images
gtk.settings_get_default().set_long_property("gtk-button-images", True, "main")

from playitslowly import mygtk
mygtk.install()

from playitslowly.pipeline import Pipeline
import gst # this has to be after the Pipeline

_ = lambda s: s # may be add gettext later

NAME = u"Play it slowly"
VERSION = "1.3.1"
WEBSITE = "http://29a.ch/playitslowly/"

if sys.platform == "win32":
    CONFIG_PATH = os.path.expanduser("~/playitslowly.json")
else:
    XDG_CONFIG_HOME = os.path.expanduser(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
    if not os.path.exists(XDG_CONFIG_HOME):
        os.mkdir(XDG_CONFIG_HOME)
    CONFIG_PATH = os.path.join(XDG_CONFIG_HOME, "playitslowly.json")

TIME_FORMAT = gst.Format(gst.FORMAT_TIME)

def in_pathlist(filename, paths = os.environ.get("PATH").split(os.pathsep)):
    """check if an application is somewhere in $PATH"""
    return any(os.path.exists(os.path.join(path, filename)) for path in paths)

class Config(dict):
    """Very simple json config file"""
    def __init__(self, path=None):
        dict.__init__(self)
        self.path = path

    def load(self):
        with open(self.path, "rb") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
        self.clear()
        self.update(data)

    def save(self):
        with open(self.path, "wb") as f:
            json.dump(self, f)


class MainWindow(gtk.Window):
    def __init__(self, sink, config):
        gtk.Window.__init__(self,gtk.WINDOW_TOPLEVEL)

        self.set_title(NAME)

        try:
            self.set_icon(mygtk.iconfactory.get_icon("playitslowly", 128))
        except gobject.GError:
            print "could not load playitslowly icon"

        self.set_default_size(500, 200)
        self.set_border_width(5)

        self.vbox = gtk.VBox()

        self.pipeline = Pipeline(sink)

        self.filedialog = mygtk.FileChooserDialog(None, self, gtk.FILE_CHOOSER_ACTION_OPEN)
        self.filedialog.connect("response", self.filechanged)
        filechooserhbox = gtk.HBox()
        self.filechooser = gtk.FileChooserButton(self.filedialog)
        filechooserhbox.pack_start(self.filechooser, True, True)
        self.recentbutton = gtk.Button(_("Recent"))
        self.recentbutton.connect("clicked", self.show_recent)
        filechooserhbox.pack_end(self.recentbutton, False, False)

        self.speedchooser = mygtk.TextScale(gtk.Adjustment(1.00, 0.10, 4.0, 0.05, 0.05))
        self.speedchooser.scale.connect("value-changed", self.speedchanged)
        self.speedchooser.scale.connect("button-press-event", self.speedpress)
        self.speedchooser.scale.connect("button-release-event", self.speedrelease)
        self.speedchangeing = False

        self.pitchchooser = mygtk.TextScale(gtk.Adjustment(0.0, -24.0, 24.0, 1.0, 1.0, 1.0))
        self.pitchchooser.scale.connect("value-changed", self.pitchchanged)

        self.pitchchooser_fine = mygtk.TextScale(gtk.Adjustment(0.0, -50, 50, 1.0, 1.0, 1.0))
        self.pitchchooser_fine.scale.connect("value-changed", self.pitchchanged)

        self.positionchooser = mygtk.TextScale(gtk.Adjustment(0.0, 0.0, 100.0))
        self.positionchooser.scale.connect("button-press-event", self.start_seeking)
        self.positionchooser.scale.connect("button-release-event", self.positionchanged)
        self.seeking = False

        self.startchooser = mygtk.TextScale(gtk.Adjustment(0.0, 0, 100.0))
        self.startchooser.scale.connect("button-press-event", self.start_seeking)
        self.startchooser.scale.connect("button-release-event", self.seeked)

        self.endchooser = mygtk.TextScale(gtk.Adjustment(1.0, 0, 100.0, 0.01, 0.01))
        self.endchooser.scale.connect("button-press-event", self.start_seeking)
        self.endchooser.scale.connect("button-release-event", self.seeked)

        self.vbox.pack_start(mygtk.form([
            (_(u"Audio File"), filechooserhbox),
            (_(u"Speed (times)"), self.speedchooser),
            (_(u"Pitch (semitones)"), self.pitchchooser),
            (_(u"Fine Pitch (cents)"), self.pitchchooser_fine),
            (_(u"Position (seconds)"), self.positionchooser),
            (_(u"Start Position (seconds)"), self.startchooser),
            (_(u"End Position (seconds)"), self.endchooser)
        ]), False, False)

        buttonbox = gtk.HButtonBox()
        self.vbox.pack_end(buttonbox, False, False)

        self.play_button = gtk.ToggleButton(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("toggled", self.play)
        self.play_button.set_use_stock(True)
        self.play_button.set_sensitive(False)
        buttonbox.pack_start(self.play_button)

        self.back_button = gtk.Button(gtk.STOCK_MEDIA_REWIND)
        self.back_button.connect("clicked", self.back)
        self.back_button.set_use_stock(True)
        self.back_button.set_sensitive(False)
        buttonbox.pack_start(self.back_button)

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

        self.connect("key-release-event", self.key_release)

        self.add(self.vbox)
        self.connect("destroy", gtk.main_quit)

        self.config = config
        self.config_saving = False
        self.load_config()

    def speedpress(self, *args):
        self.speedchangeing = True

    def speedrelease(self, *args):
        self.speedchangeing = False
        self.speedchanged()

    def get_pitch(self):
        return self.pitchchooser.get_value()+self.pitchchooser_fine.get_value()*0.01

    def set_pitch(self, value):
        semitones = round(value)
        cents = round((value-semitones)*100)
        self.pitchchooser.set_value(semitones)
        self.pitchchooser_fine.set_value(cents)

    def add_recent(self, uri):
        manager = gtk.recent_manager_get_default()
        app_exec = "playitslowly \"%s\"" % uri
        mime_type = mimetypes.guess_type(uri)[0]
        if mime_type:
            manager.add_full(uri, {
                "app_name": "playitslowly",
                "app_exec": "playitslowly",
                "mime_type": mime_type
            })


    def show_recent(self, sender=None):
        dialog = gtk.RecentChooserDialog(_("Recent Files"), self, None,
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                 gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        filter = gtk.RecentFilter()
        filter.set_name("playitslowly")
        filter.add_application("playitslowly")
        dialog.add_filter(filter)

        filter2 = gtk.RecentFilter()
        filter2.set_name(_("All"))
        filter2.add_mime_type("audio/*")
        dialog.add_filter(filter2)

        dialog.set_filter(filter)

        if dialog.run() == gtk.RESPONSE_OK and dialog.get_current_item():
            uri = dialog.get_current_item().get_uri()
            self.filedialog.set_uri(dialog.get_current_item().get_uri())
            self.filechanged(uri=uri)
        dialog.destroy()

    def load_config(self):
        self.config_saving = True # do not save while loading
        lastfile = self.config.get("lastfile")
        if lastfile:
            self.filedialog.set_uri(lastfile)
            self.filechanged(uri=lastfile)
        self.config_saving = False

    def reset_settings(self):
        self.speedchooser.set_value(1.0)
        self.speedchanged()
        self.set_pitch(0.0)
        self.startchooser.get_adjustment().set_property("upper", 0.0)
        self.startchooser.set_value(0.0)
        self.endchooser.get_adjustment().set_property("upper", 1.0)
        self.endchooser.set_value(1.0)

    def load_file_settings(self, filename):
        self.add_recent(filename)
        if not self.config or not filename in self.config["files"]:
            self.reset_settings()
            self.pipeline.set_file(self.filedialog.get_uri())
            self.pipeline.pause()
            gobject.timeout_add(100, self.update_position)
            return
        settings = self.config["files"][filename]
        self.speedchooser.set_value(settings["speed"])
        self.set_pitch(settings["pitch"])
        self.startchooser.get_adjustment().set_property("upper", settings["duration"])
        self.startchooser.set_value(settings["start"])
        self.endchooser.get_adjustment().set_property("upper", settings["duration"] or 1.0)
        self.endchooser.set_value(settings["end"])
        self.volume_button.set_value(settings["volume"])

    def save_config(self):
        """saves the config file with a delay"""
        if self.config_saving:
            return
        gobject.timeout_add(1000, self.save_config_now)
        self.config_saving = True

    def save_config_now(self):
        self.config_saving = False
        lastfile = self.filedialog.get_uri()
        self.config["lastfile"] = lastfile
        settings = {}
        settings["speed"] = self.speedchooser.get_value()
        settings["pitch"] = self.get_pitch()
        settings["duration"] = self.startchooser.get_adjustment().get_property("upper")
        settings["start"] = self.startchooser.get_value()
        settings["end"] = self.endchooser.get_value()
        settings["volume"] = self.volume_button.get_value()
        self.config.setdefault("files", {})[lastfile] = settings

        self.config.save()

    def key_release(self, sender, event):
        if not event.state & gtk.gdk.CONTROL_MASK:
            return
        try:
            val = int(chr(event.keyval))
        except ValueError:
            return
        self.back(self, val)

    def volumechanged(self, sender, foo):
        self.pipeline.set_volume(sender.get_value())
        self.save_config()

    def save(self, sender):
        dialog = mygtk.FileChooserDialog(_(u"Save modified version as"),
                self, gtk.FILE_CHOOSER_ACTION_SAVE)
        dialog.set_current_name("export.wav")
        if dialog.run() == gtk.RESPONSE_OK:
            self.pipeline.set_file(self.filedialog.get_uri())
            self.foo = self.pipeline.save_file(dialog.get_filename())
        dialog.destroy()

    def filechanged(self, sender=None, response_id=gtk.RESPONSE_OK, uri=None):
        if response_id != gtk.RESPONSE_OK:
            return

        self.play_button.set_sensitive(True)
        self.back_button.set_sensitive(True)
        self.save_as_button.set_sensitive(True)
        self.play_button.set_active(False)

        self.pipeline.reset()
        self.seek(0)
        self.save_config()

        if uri:
            self.load_file_settings(uri)
        else:
            # for what ever reason filedialog.get_uri() is sometimes None until the
            # mainloop ran through
            gobject.timeout_add(1, lambda: self.load_file_settings(self.filedialog.get_uri()))

    def start_seeking(self, sender, foo):
        self.seeking = True

    def seeked(self, sender, foo):
        self.seeking = False
        self.save_config()

    def positionchanged(self, sender, foo):
        self.seek(sender.get_value())
        self.seeking = False
        self.save_config()

    def seek(self, pos):
        if self.positionchooser.get_value() != pos:
            self.positionchooser.set_value(pos)
        pos = self.pipeline.pipe_time(pos)
        self.pipeline.playbin.seek_simple(TIME_FORMAT, gst.SEEK_FLAG_FLUSH, pos)

    def speedchanged(self, *args):
        if self.speedchangeing:
            return
        pos = self.positionchooser.get_value()
        self.pipeline.set_speed(self.speedchooser.get_value())
        # hack to get gstreamer to calculate the position again
        self.seek(pos)
        self.save_config()

    def pitchchanged(self, sender):
        self.pipeline.set_pitch(2**(self.get_pitch()/12.0))
        self.save_config()

    def back(self, sender, amount=None):
        try:
            position, fmt = self.pipeline.playbin.query_position(TIME_FORMAT, None)
        except gst.QueryError:
            return
        if amount:
            t = self.pipeline.song_time(position)-amount
            if t < 0:
                t = 0
        else:
            t = 0
        self.seek(t)

    def play(self, sender):
        if sender.get_active():
            self.pipeline.set_file(self.filedialog.get_uri())
            self.pipeline.play()
            gobject.timeout_add(100, self.update_position)
        else:
            self.pipeline.pause()

    def update_position(self):
        """update the position of the scales and pipeline"""
        if self.seeking:
            return self.play_button.get_active()
        try:
            position, fmt = self.pipeline.playbin.query_position(TIME_FORMAT, None)
            duration, fmt = self.pipeline.playbin.query_duration(TIME_FORMAT, None)
        except gst.QueryError:
            return self.play_button.get_active()
        position = self.pipeline.song_time(position)
        duration = self.pipeline.song_time(duration)
        start = self.startchooser.get_value()
        end = self.endchooser.get_value()

        if end <= start:
            self.play_button.set_active(False)
            return False

        if position >= end or position < start:
            self.seek(start+0.01)
            return True

        if self.positionchooser.get_adjustment().get_property("upper") != duration:
            self.positionchooser.set_range(0.0, duration)
            self.save_config()
        end = self.endchooser.get_adjustment()
        delta = end.value-end.upper
        if delta <= -duration:
            delta = 0
        self.startchooser.set_range(0.0, duration)
        self.endchooser.set_range(0.0, duration)
        self.endchooser.set_value(duration+delta)
        self.positionchooser.set_value(position)
        self.positionchooser.queue_draw()
        return self.play_button.get_active()

    def about(self, sender):
        """show an about dialog"""
        about = gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_logo(mygtk.iconfactory.get_icon("playitslowly", 128))
        about.set_name(NAME)
        about.set_version(VERSION)
        about.set_authors(["Jonas Wagner"])
        about.set_translator_credits(_("translator-credits"))
        about.set_copyright("Copyright (c) 2009 - 2010 Jonas Wagner")
        about.set_website(WEBSITE)
        about.set_website_label(WEBSITE)
        about.set_license("""
Copyright (C) 2009 - 2010 Jonas Wagner
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
    sink = "autoaudiosink"
    if in_pathlist("gstreamer-properties"):
        sink = "gconfaudiosink"
    options, arguments = getopt.getopt(sys.argv[1:], "h", ["help", "sink="])
    for option, argument in options:
        if option in ("-h", "--help"):
            print "Usage: playitslowly [OPTIONS]... [FILE]"
            print "Options:"
            print '--sink=sink      specify gstreamer sink for playback'
            sys.exit()
        elif option == "--sink":
            print "sink", argument
            sink = argument
    config = Config(CONFIG_PATH)
    try:
        config.load()
    except IOError:
        pass
    sink = gst.parse_bin_from_description(sink, True)
    win = MainWindow(sink, config)
    if arguments:
        uri = arguments[0]
        if not uri.startswith("file://"):
            uri = "file://" + os.path.abspath(uri)

        win.filechooser.set_uri(uri)
        win.filechanged(uri=uri)
    win.show_all()
    gtk.main()

if __name__ == "__main__":
    main()
