#!/usr/bin/env python3
# vim: set fileencoding=utf-8 :
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
import madmom 
import librosa
import numpy as np
import soundfile as sf
from pydub import AudioSegment
import io
from os.path import expanduser
import scipy.io.wavfile

import getopt
import mimetypes
import os
import sys

try:
    import json
except ImportError:
    import simplejson as json

import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GObject, Gst, Gio, Gdk

GObject.threads_init()
Gst.init(None)

from playitslowly.pipeline import Pipeline

# always enable button images
Gtk.Settings.get_default().set_long_property("gtk-button-images", True, "main")

from playitslowly import myGtk
myGtk.install()


_ = lambda s: s # may be add gettext later

NAME = "Play it Slowly"
VERSION = "1.5.1"
WEBSITE = "http://29a.ch/playitslowly/"

if sys.platform == "win32":
    CONFIG_PATH = os.path.expanduser("~/playitslowly.json")
else:
    XDG_CONFIG_HOME = os.path.expanduser(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
    if not os.path.exists(XDG_CONFIG_HOME):
        os.mkdir(XDG_CONFIG_HOME)
    CONFIG_PATH = os.path.join(XDG_CONFIG_HOME, "playitslowly.json")

TIME_FORMAT = Gst.Format(Gst.Format.TIME)

def in_pathlist(filename, paths = os.environ.get("PATH").split(os.pathsep)):
    """check if an application is somewhere in $PATH"""
    return any(os.path.exists(os.path.join(path, filename)) for path in paths)

class Config(dict):
    """Very simple json config file"""
    def __init__(self, path=None):
        dict.__init__(self)
        self.path = path

    def load(self):
        with open(self.path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print("Error loading config: %s", e)
                data = {}
        self.clear()
        self.update(data)

    def save(self):
        with open(self.path, mode="w", encoding="utf-8") as f:
            json.dump(self, f)


class MainWindow(Gtk.Window):
    def __init__(self, sink, config):
        Gtk.Window.__init__(self, Gtk.WindowType.TOPLEVEL)

        self.set_title(NAME)
        try:
            self.set_icon(myGtk.iconfactory.get_icon("playitslowly", 128))
        except GObject.GError:
            print("could not load playitslowly icon")

        self.set_default_size(600, 200)
        self.set_border_width(5)

        self.vbox = Gtk.VBox()
        self.accel_group = Gtk.AccelGroup()
        self.add_accel_group(self.accel_group)

        self.pipeline = Pipeline(sink)

        self.filedialog = myGtk.FileChooserDialog(None, self, Gtk.FileChooserAction.OPEN)
        self.filedialog.connect("response", self.filechanged)
        self.filedialog.set_local_only(False)
        filechooserhbox = Gtk.HBox()
        self.filechooser = Gtk.FileChooserButton.new_with_dialog(self.filedialog)
        self.filechooser.set_local_only(False)
        filechooserhbox.pack_start(self.filechooser, True, True, 0)
        self.recentbutton = Gtk.Button(_("Recent"))
        self.recentbutton.connect("clicked", self.show_recent)
        filechooserhbox.pack_end(self.recentbutton, False, False, 0)

        self.speedchooser = myGtk.TextScaleReset(Gtk.Adjustment.new(1.00, 0.10, 4.0, 0.05, 0.05, 0))
        self.speedchooser.scale.connect("value-changed", self.speedchanged)
        self.speedchooser.scale.connect("button-press-event", self.speedpress)
        self.speedchooser.scale.connect("button-release-event", self.speedrelease)
        self.speedchangeing = False

        pitch_adjustment = Gtk.Adjustment.new(0.0, -24.0, 24.0, 1.0, 1.0, 1.0)
        self.pitchchooser = myGtk.TextScaleReset(pitch_adjustment)
        self.pitchchooser.scale.connect("value-changed", self.pitchchanged)

        self.pitchchooser_fine = myGtk.TextScaleReset(Gtk.Adjustment.new(0.0, -50, 50, 1.0, 1.0, 1.0))
        self.pitchchooser_fine.scale.connect("value-changed", self.pitchchanged)

        self.positionchooser = myGtk.ClockScale(Gtk.Adjustment.new(0.0, 0.0, 100.0, 0, 0, 0))
        self.positionchooser.scale.connect("button-press-event", self.start_seeking)
        self.positionchooser.scale.connect("button-release-event", self.positionchanged)
        self.seeking = False

        self.startchooser = myGtk.TextScaleWithCurPos(self.positionchooser, Gtk.Adjustment.new(0.0, 0, 100.0, 0, 0, 0))
        self.startchooser.scale.connect("button-press-event", self.start_seeking)
        self.startchooser.scale.connect("button-release-event", self.seeked)
        self.startchooser.add_accelerator("clicked", self.accel_group, ord('['), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.startchooser.add_accelerator("clicked", self.accel_group, ord('['), 0, Gtk.AccelFlags.VISIBLE)

        self.endchooser = myGtk.TextScaleWithCurPos(self.positionchooser, Gtk.Adjustment.new(1.0, 0, 100.0, 0.01, 0.01, 0))
        self.endchooser.scale.connect("button-press-event", self.start_seeking)
        self.endchooser.scale.connect("button-release-event", self.seeked)
        self.endchooser.add_accelerator("clicked", self.accel_group, ord(']'), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        self.endchooser.add_accelerator("clicked", self.accel_group, ord(']'), 0, Gtk.AccelFlags.VISIBLE)

        self.vbox.pack_start(filechooserhbox, False, False, 0)
        self.vbox.pack_start(self.positionchooser, True, True, 0)
        self.vbox.pack_start(myGtk.form([(_("Speed (times)"), self.speedchooser),
            (_("Pitch (semitones)"), self.pitchchooser),
            (_("Fine Pitch (cents)"), self.pitchchooser_fine),
            (_("Start Position (seconds)"), self.startchooser),
            (_("End Position (seconds)"), self.endchooser)
        ]), False, False, 0)

        buttonbox = Gtk.HButtonBox()
        myGtk.add_style_class(buttonbox, 'buttonBox')
        self.vbox.pack_end(buttonbox, False, False, 0)

        #self.tempo_str = 
        #label = Gtk.Label(label=)
        #buttonbox.pack_start(label, True, True, 0)

        self.bpm_button = Gtk.CheckButton(label="BPM")
        self.bpm_button.connect("toggled", self.add_bpm)
        buttonbox.pack_start(self.bpm_button, False, False, 0)

        self.play_button = Gtk.ToggleButton(stock=Gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("toggled", self.play)
        self.play_button.set_use_stock(True)
        self.play_button.set_sensitive(False)
        buttonbox.pack_start(self.play_button, True, True, 0)
        self.play_button.add_accelerator("clicked", self.accel_group, ord(' '), 0, Gtk.AccelFlags.VISIBLE)

        self.back_button = Gtk.Button.new_from_stock(Gtk.STOCK_MEDIA_REWIND)
        self.back_button.connect("clicked", self.back)
        #self.back_button.set_use_stock(True)
        self.back_button.set_sensitive(False)
        buttonbox.pack_start(self.back_button, True, True, 0)

        self.volume_button = Gtk.VolumeButton()
        self.volume_button.set_value(1.0)
        self.volume_button.set_relief(Gtk.ReliefStyle.NORMAL)
        self.volume_button.connect("value-changed", self.volumechanged)
        buttonbox.pack_start(self.volume_button, True, True, 0)

        self.save_as_button = Gtk.Button.new_from_stock(Gtk.STOCK_SAVE_AS)
        self.save_as_button.connect("clicked", self.save)
        self.save_as_button.set_sensitive(False)
        buttonbox.pack_start(self.save_as_button, True, True, 0)

        button_about = Gtk.Button.new_from_stock(Gtk.STOCK_ABOUT)
        button_about.connect("clicked", self.about)
        buttonbox.pack_end(button_about, True, True, 0)

        self.connect("key-release-event", self.key_release)

        self.add(self.vbox)
        self.connect("destroy", Gtk.main_quit)

        self.config = config
        self.config_saving = False
        self.load_config() 

        self.path_combined_audio = " "
        self.original_song_str = self.filedialog.get_uri() 

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
        manager = Gtk.RecentManager.get_default()
        app_exec = "playitslowly \"%s\"" % uri
        mime_type, certain = Gio.content_type_guess(uri)
        if mime_type:
            recent_data = Gtk.RecentData()
            recent_data.app_name = "playitslowly"
            recent_data.app_exec = "playitslowly"
            recent_data.mime_type = mime_type
            manager.add_full(uri, recent_data)
            print(app_exec, mime_type)

    def bpm_notification(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            text="Analycing Audio",
        )
        dialog.format_secondary_text(
            "This may take a time..."
        )
        dialog.run()

        #dialog.destroy()

    def bpm_calculation(self):
        str_song = self.filedialog.get_uri()[7:]
        str_song = str_song.replace("%20", " ")
        self.original_song_str = self.filedialog.get_uri()
        #print(self.original_song_str)
        # read audio file 
        song = AudioSegment.from_file(str_song)
        sound = song.set_frame_rate(librosa.get_samplerate(str_song))
        channel_sounds = song.split_to_mono()
        samples = [s.get_array_of_samples() for s in channel_sounds]

        x = np.array(samples).T.astype(np.float32)
        x /= np.iinfo(samples[0].typecode).max

        sr = librosa.get_samplerate(str_song) 
        # dbn tracker
        proc = madmom.features.beats.DBNBeatTrackingProcessor(fps=100)
        act = madmom.features.beats.RNNBeatProcessor()(str_song)
        # write clicks over track
        beat_times = proc(act)
        clicks = librosa.clicks(beat_times, sr=sr, length=len(x))

        wav_io = io.BytesIO()
        scipy.io.wavfile.write(wav_io, sr, clicks)
        wav_io.seek(0)
        clicks_audio = AudioSegment.from_wav(wav_io)

        combined = song.overlay(clicks_audio)
        self.path_combined_audio = expanduser("~") + "/" + os.path.basename(self.original_song_str.replace("%20", "_")) 
        combined.export(self.path_combined_audio, format='wav')

        #self.filedialog.set_uri("file://" + self.path_combined_audio)
        self.pipeline.pause()
        self.pipeline.reset()
        self.pipeline.set_file("file://" + self.path_combined_audio)
        GObject.timeout_add(100, self.update_position)

    def add_bpm(self, button):
        if os.path.isfile(expanduser("~") + "/" + os.path.basename(self.filedialog.get_uri().replace("%20","_"))) == False:
            self.bpm_calculation()
            self.save_config()
        else:
            self.path_combined_audio = expanduser("~") + "/" + os.path.basename(self.filedialog.get_uri().replace("%20", "_"))
            if self.bpm_button.get_active() == False:
                #self.filedialog.set_uri(self.original_song_str)
                #self.pipeline.pause()
                self.pipeline.reset()
                #self.pipeline.set_file(self.original_song_str)
                self.filedialog.set_uri(self.original_song_str)
                GObject.timeout_add(100, self.update_position)
            else:
                #self.filedialog.set_uri("file://" + self.path_combined_audio)
                #self.pipeline.pause()
                self.pipeline.reset()
                set_string = "file://" + self.path_combined_audio
                #self.pipeline.set_file(set_string)
                self.filedialog.set_uri(set_string)
                GObject.timeout_add(100, self.update_position)

        #self.pipeline.set_file("file://" + self.path_combined_audio)
        #self.bpm_calculation()

    def show_recent(self, sender=None):
        dialog = Gtk.RecentChooserDialog(_("Recent Files"), self, None,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        filter = Gtk.RecentFilter()
        filter.set_name("playitslowly")
        filter.add_application("playitslowly")
        dialog.add_filter(filter)

        filter2 = Gtk.RecentFilter()
        filter2.set_name(_("All"))
        filter2.add_mime_type("audio/*")
        dialog.add_filter(filter2)

        dialog.set_local_only(False)

        dialog.set_filter(filter)

        if dialog.run() == Gtk.ResponseType.OK and dialog.get_current_item():
            uri = dialog.get_current_item().get_uri()
            if isinstance(uri, bytes):
                uri = uri.decode('utf-8')
            self.set_uri(uri)
        dialog.destroy()

    def set_uri(self, uri):
        print(repr(uri))
        self.filedialog.set_uri(uri)
        self.filechooser.set_uri(uri)
        self.filechanged(uri=uri)

    def load_config(self):
        self.config_saving = True # do not save while loading
        lastfile = self.config.get("lastfile")
        if lastfile:
            self.set_uri(lastfile)
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
        print("load_file_settings", filename)
        self.add_recent(filename)
        if not self.config or not filename in self.config["files"]:
            self.reset_settings()
            self.pipeline.set_file(filename)
            self.pipeline.pause()
            GObject.timeout_add(100, self.update_position)
            return
        settings = self.config["files"][filename]
        self.speedchooser.set_value(settings["speed"])
        self.set_pitch(settings["pitch"])
        self.startchooser.get_adjustment().set_property("upper", settings["duration"])
        self.startchooser.set_value(settings["start"])
        self.endchooser.get_adjustment().set_property("upper", settings["duration"] or 1.0)
        self.endchooser.set_value(settings["end"])
        self.volume_button.set_value(settings["volume"])
        self.path_combined_audio = settings["combined_audio"]

    def save_config(self):
        """saves the config file with a delay"""
        if self.config_saving:
            return
        GObject.timeout_add(1000, self.save_config_now)
        self.config_saving = True

    def save_config_now(self):
        self.config_saving = False
        lastfile = self.original_song_str #self.filedialog.get_uri()
        self.config["lastfile"] = lastfile #self.original_song_str
        settings = {}
        settings["speed"] = self.speedchooser.get_value()
        settings["pitch"] = self.get_pitch()
        settings["duration"] = self.startchooser.get_adjustment().get_property("upper")
        settings["start"] = self.startchooser.get_value()
        settings["end"] = self.endchooser.get_value()
        settings["volume"] = self.volume_button.get_value()
        settings["combined_audio"] = self.path_combined_audio
        self.config.setdefault("files", {})[lastfile] = settings

        self.config.save()

    def key_release(self, sender, event):
        if not event.get_state() & Gdk.ModifierType.CONTROL_MASK:
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
        dialog = myGtk.FileChooserDialog(_("Save modified version as"),
                self, Gtk.FileChooserAction.SAVE)
        dialog.set_current_name("export.wav")
        if dialog.run() == Gtk.ResponseType.OK:
            self.pipeline.set_file(self.filedialog.get_uri())
            self.foo = self.pipeline.save_file(dialog.get_filename())
        dialog.destroy()

    def filechanged(self, sender=None, response_id=Gtk.ResponseType.OK, uri=None):
        print("file changed", uri)
        if response_id != Gtk.ResponseType.OK:
            return

        self.play_button.set_sensitive(True)
        self.back_button.set_sensitive(True)
        self.save_as_button.set_sensitive(True)
        self.play_button.set_active(False)
        self.bpm_button.set_active(False)

        self.pipeline.reset()
        self.seek(0)
        self.save_config()

        self.original_song_str = self.filedialog.get_uri() 

        if uri:
            self.load_file_settings(uri)
        else:
            # for what ever reason filedialog.get_uri() is sometimes None until the
            # mainloop ran through
            GObject.timeout_add(1, lambda: self.load_file_settings(self.filedialog.get_uri()))

    def start_seeking(self, sender, foo):
        self.seeking = True

    def seeked(self, sender, foo):
        self.seeking = False
        self.save_config()

    def positionchanged(self, sender, foo):
        self.seek(sender.get_value())
        self.seeking = False
        self.save_config()

    def seek(self, pos=0):
        if self.positionchooser.get_value() != pos:
            self.positionchooser.set_value(pos)
        pos = self.pipeline.pipe_time(pos)
        self.pipeline.playbin.seek_simple(TIME_FORMAT, Gst.SeekFlags.FLUSH, pos or 0)

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
        position, fmt = self.pipeline.playbin.query_position(TIME_FORMAT)
        if position is None:
            return
        if amount:
            t = self.pipeline.song_time(position)-amount
            if t < 0:
                t = 0
        else:
            t = self.startchooser.get_value()
        self.seek(t)

    def play(self, sender):
        if sender.get_active():
            self.pipeline.set_file(self.filedialog.get_uri())
            self.pipeline.play()
            GObject.timeout_add(100, self.update_position)
        else:
            self.pipeline.pause()

    def update_position(self):
        """update the position of the scales and pipeline"""
        if self.seeking:
            return self.play_button.get_active()

        _, position = self.pipeline.playbin.query_position(TIME_FORMAT)
        _, duration = self.pipeline.playbin.query_duration(TIME_FORMAT)
        if position is None or duration is None:
            return self.play_button.get_active()
        position = position
        duration = duration
        position = self.pipeline.song_time(position)
        duration = self.pipeline.song_time(duration)

        if self.positionchooser.get_adjustment().get_property("upper") != duration:
            self.positionchooser.set_range(0.0, duration)
            self.save_config()

        end_adjustment = self.endchooser.get_adjustment()
        delta = end_adjustment.get_value() - end_adjustment.get_upper()

        if delta <= -duration:
            delta = 0

        self.startchooser.set_range(0.0, duration)
        self.endchooser.set_range(0.0, duration)
        self.endchooser.set_value(duration+delta)

        self.positionchooser.set_value(position)
        self.positionchooser.queue_draw()

        start = self.startchooser.get_value()
        end = self.endchooser.get_value()

        if end <= start:
            self.play_button.set_active(False)
            return False

        if position >= end or position < start:
            self.seek(start+0.01)
            return True

        return self.play_button.get_active()

    def about(self, sender):
        """show an about dialog"""
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_logo(myGtk.iconfactory.get_icon("playitslowly", 128))
        about.set_name(NAME)
        about.set_program_name(NAME)
        about.set_version(VERSION)
        about.set_authors(["Jonas Wagner", "Elias Dorneles"])
        about.set_translator_credits(_("translator-credits"))
        about.set_copyright("Copyright (c) 2009 - 2015 Jonas Wagner")
        about.set_website(WEBSITE)
        about.set_website_label(WEBSITE)
        about.set_license("""
Copyright (C) 2009 - 2015 Jonas Wagner
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

css = b"""
.buttonBox GtkButton GtkLabel { padding-left: 4px; }
"""





def main():
    sink = "autoaudiosink"
    if in_pathlist("gstreamer-properties"):
        sink = "gconfaudiosink"
    options, arguments = getopt.getopt(sys.argv[1:], "h", ["help", "sink="])
    for option, argument in options:
        if option in ("-h", "--help"):
            print("Usage: playitslowly [OPTIONS]... [FILE]")
            print("Options:")
            print('--sink=sink      specify gstreamer sink for playback')
            sys.exit()
        elif option == "--sink":
            print("sink", argument)
            sink = argument
    config = Config(CONFIG_PATH)
    try:
        config.load()
    except IOError:
        pass

    style_provider = Gtk.CssProvider()

    style_provider.load_from_data(css)

    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), 
        style_provider,     
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    win = MainWindow(sink, config)

    if arguments:
        uri = arguments[0]
        if not uri.startswith("file://"):
            uri = "file://" + os.path.abspath(uri)
        win.set_uri(uri)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()
