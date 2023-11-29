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

from gi.repository import Gtk, GObject
import math
import sys
from datetime import timedelta
import collections

_ = lambda s: s

buttons_ok_cancel = (Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL,Gtk.STOCK_OPEN,Gtk.ResponseType.OK)
class FileChooserDialog(Gtk.FileChooserDialog):
    """a file chooser dialog which automatically sets the correct buttons!"""
    def __init__(self, title=None, parent=None, action=None):
        if action == Gtk.FileChooserAction.SAVE:
            buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE ,Gtk.ResponseType.OK)
            title = title or _("Save File")
        else:
            if action == Gtk.FileChooserAction.SELECT_FOLDER:
                title = title or _("Select Folder")
            elif action == Gtk.FileChooserAction.CREATE_FOLDER:
                title = title or _("Create Folder")
            else:
                title = title or _("Open a File")
            buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN ,Gtk.ResponseType.OK)
        Gtk.FileChooserDialog.__init__(self, title, parent, action, buttons)

class IconFactory:
    def __init__(self, icon_theme):
        self.cache = {}
        self.icon_theme = icon_theme

    def guess_icon(self, filename, size):
        return self.get_icon(self.guess_icon_name(filename), size)

    def get_icon(self, name, size):
        # damn it! why did no one tell me I have to cache this!!!
        if not (name, size) in self.cache:
            try:
                self.cache[(name, size)] = self.icon_theme.load_icon(name,
                        size, 0)
            except GObject.GError as e:
                #logger.exception("Unable to load icon %r probably your "
                #        "icon theme isn't conforming to the icon naming "
                #        "convention. You might want to try the tango icon "
                #        "theme", name)
                return None
        return self.cache[(name, size)]

    def get_image(self, name, size):
        pixbuf = self.get_icon(name, size)
        img = Gtk.Image()
        img.set_from_pixbuf(pixbuf)
        return img

    def has_icon(self, name):
        return self.icon_theme.has_icon(name)

icon_theme = Gtk.IconTheme.get_default()
iconfactory = IconFactory(icon_theme)

def idle_do(func, *args):
    """wrapper arround idle_add that will always run once"""
    def wrapper(*args):
        # throw away the result of the function!
        func(*args)
    GObject.idle_add(wrapper, *args)

def scrolled(widget, shadow=Gtk.ShadowType.NONE):
    window = Gtk.ScrolledWindow()
    window.set_shadow_type(shadow)
    window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    window.add_with_viewport(widget)
    return window


def make_table(widgets):
    """return a Gtk.Table containing all the widgets"""
    columns = max(list(map(len, widgets)))
    table = Gtk.Table(len(widgets), columns, False)
    for y, row in enumerate(widgets):
        for x, widget in enumerate(row):
            if widget:
                table.attach(widget, x, x+1, y, y+1,
                        xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, xpadding=4, ypadding=4)
    return table

class Gtklock:
    """A context manger for the Gdk.threads_*

    can be used like this
    >> with Gtklock:
    >>     pass
    """
    @staticmethod
    def __enter__():
        Gdk.threads_enter()

    @staticmethod
    def __exit__(*args):
        Gdk.threads_leave()

def Gtk_yield():
    """process all the peding events in the mainloop"""
    while Gtk.events_pending():
         Gtk.main_iteration()

class IconButton(Gtk.Button):
    def __init__(self, icon, size=None, label=None):
        GObject.GObject.__init__(self)
        self.size = size or Gtk.IconSize.BUTTON
        self.hbox = Gtk.HBox()
        self.add(self.hbox)
        self.img = None
        self.set_icon(icon)
        self.label = None
        self.set_label(label)

    def set_label(self, label):
        if self.label:
            self.label.set_text(label)
        else:
            self.label = Gtk.Label(label=label)
            self.hbox.pack_end(self.label, True, True, 0)

    def set_icon(self, icon):
        if self.img:
            self.img.set_from_pixbuf(iconfactory.get_icon(icon, self.size))
        else:
            self.img = iconfactory.get_image(icon, self.size)
            self.hbox.pack_start(self.img, True, True, 0)
        self._icon = icon
    icon = property(lambda self: self._icon, set_icon)

class IconMenuItem(Gtk.ImageMenuItem):
    icon_size = Gtk.icon_size_lookup(Gtk.IconSize.MENU)[0]
    def __init__(self, icon, text):
        GObject.GObject.__init__(self)
        self.set_image(iconfactory.get_image(icon, self.icon_size))
        label = Gtk.Label(label=text)
        label.set_alignment(0.0, 0.5)
        self.add(label)
        self.show_all()

def show_error(msg):
    """Show a 'nice' errbox"""
    dialog = Gtk.MessageDialog(type=Gtk.MessageType.ERROR, message_format=str(msg),
            buttons=Gtk.ButtonsType.OK)
    dialog.set_title(_("Error"))
    # dialog.run() - this breaks when called from GObject.idle_add
    # dialog.hide()
    # dialog.destroy
    dialog.show()
    dialog.connect("response", lambda dialog, response: dialog.destroy())
    return dialog

def make_menu(entries, menu):
    for entry in entries:
        if entry is None:
            sub = None
            item = Gtk.SeparatorMenuItem()
        else:
            key, sub = entry
            if isinstance(key, tuple):
                item = IconMenuItem(*key)
            elif key.startswith("Gtk-"):
                item = Gtk.ImageMenuItem(stock_id=key)
            else:
                item = Gtk.MenuItem(key)
        if sub:
            if isinstance(sub, collections.Callable):
                item.connect("activate", sub)
            else:
                submenu = Gtk.Menu()
                item.set_submenu(submenu)
                make_menu(sub, submenu)
        menu.append(item)

def form(rows):
    table = Gtk.Table(len(rows), 2, False)
    for y, (text, widget) in enumerate(rows):
        label = Gtk.Label(label=text)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, y, y+1, xoptions=Gtk.AttachOptions.SHRINK|Gtk.AttachOptions.FILL, xpadding=4, ypadding=4)
        table.attach(widget, 1, 2, y, y+1, xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, xpadding=4, ypadding=4)
    return table

def make_table(widgets):
    """return a Gtk.Table containing all the widgets"""
    columns = max(list(map(len, widgets)))
    table = Gtk.Table(len(widgets), columns, False)
    for y, row in enumerate(widgets):
        for x, widget in enumerate(row):
            table.attach(widget, x, x+1, y, y+1, xoptions=Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL,
                    xpadding=4, ypadding=4)
    return table

class Scale(object):
    """A scale that adheres to increment steps"""
    def __init__(self):
        self.connect("change-value", self.adjust)

    def adjust(self, range, scroll, value):
        adj = self.get_adjustment()
        lower = adj.get_property('lower')
        upper = adj.get_property('upper')
        incr = adj.get_property('step-increment') or 1
        value -= (value % incr)
        self.set_value(min(max(lower, value), upper))
        return True

class VScale(Gtk.VScale, Scale):
    def __init__(self, *args):
        Gtk.VScale.__init__(self, *args)
        Scale.__init__(self)

class HScale(Gtk.HScale, Scale):
    def __init__(self, *args):
        Gtk.HScale.__init__(self)
        Scale.__init__(self)
        self.set_adjustment(*args)

class ClockScale(Gtk.VBox):
    def __init__(self, *args):
        GObject.GObject.__init__(self)
        self.clocklabel = Gtk.Label()

        self.range_max = 0.0

        # slider
        self.scale = HScale(*args)
        self.scale.set_draw_value(False)
        self.set_value = self.scale.set_value
        self.get_value = self.scale.get_value
        self.get_adjustment = self.scale.get_adjustment
        self.set_adjustment = self.scale.set_adjustment

        self.update_clock()
        self.scale.connect("value-changed", self.update_clock)

        self.pack_start(self.clocklabel, True, True, 0)
        self.pack_start(self.scale, True, True, 0)

    def update_clock(self, sender=None):
        self.clocklabel.set_markup(self.format(self.get_value(),
                                               self.range_max))

    def format(self, value, max):
        hms, ms = self.split_time(value)
        max_hms, max_ms = self.split_time(max)
        format_str = '<span size="xx-large" weight="bold">{}<span size="medium">.{}</span></span>' + \
            '<span size="xx-large" > / </span>' + \
            '<span size="xx-large" weight="bold">{}<span size="medium">.{}</span></span>'
        return format_str.format(hms, ms, max_hms, max_ms)

    def set_range(self, min, max):
        "Set range for scale."
        self.range_max = max
        self.scale.set_range(min, max)

    def split_time(self, time):
        """Split time into two parts, one is h:mm:ss and the other millisecond"""
        hms = str(timedelta(seconds=time))[:7]
        ms = str(timedelta(seconds=time))[8:11]
        if ms == '':
            ms = '000'
        return hms, ms

class TextScale(Gtk.HBox):
    format = "%.2f"
    size = 6
    def __init__(self, *args):
        GObject.GObject.__init__(self)
        self.from_text = False

        self.entry = Gtk.Entry()

        self.scale = HScale(*args)
        self.scale.set_draw_value(False)
        self.set_value = self.scale.set_value
        self.get_value = self.scale.get_value
        self.get_adjustment = self.scale.get_adjustment
        self.set_adjustment = self.scale.set_adjustment
        self.set_range = self.scale.set_range

        #n = len(self.format % self.scale.get_adjustment().get_upper())
        self.entry.set_width_chars(self.size)
        if hasattr(self.entry, 'set_max_width_chars'):
            self.entry.set_max_width_chars(self.size)

        self.update_text()
        self.scale.connect("value-changed", self.update_text)
        self.entry.connect("changed", self.update_scale)

        self.pack_start(self.scale, True, True, 4)
        self.pack_start(self.entry, False, False, 4)

        self.entry.set_alignment(1.0)

    def update_text(self, sender=None):
        if not self.from_text:
            self.entry.set_text(self.format % self.get_value())

    def update_scale(self, sender=None):
        self.from_text = True
        try:
            self.set_value(float(self.entry.get_text()))
        except ValueError:
            pass
        self.from_text = False

class TextScaleReset(TextScale):
    def __init__(self, *args):
        TextScale.__init__(self, *args)
        self.reset_button = Gtk.Button.new_with_label(_('Reset'))
        self.reset_button.set_size_request(64, -1)
        add_style_class(self.reset_button, 'textScaleButton')
        self.reset_button.connect("clicked", self.reset_to_default)
        self.pack_start(self.reset_button, False, False, 0)
        self.reorder_child(self.reset_button, 1)
        self.default_value = self.get_value()
        self.add_accelerator = self.reset_button.add_accelerator
    def reset_to_default(self, sender=None):
        self.set_value(self.default_value)

# TODO: substitute for a decorator?
class TextScaleWithCurPos(TextScale):
    def __init__(self, slider, *args):
        TextScale.__init__(self, *args)
        self.now_button = Gtk.Button(_('Now'))
        self.now_button.set_size_request(64, -1)
        self.now_button.connect("clicked", self.update_to_current_position)
        self.pack_start(self.now_button, False, False, 0)
        self.reorder_child(self.now_button, 1)
        self.slider = slider
        self.add_accelerator = self.now_button.add_accelerator
    def update_to_current_position(self, sender=None):
        self.set_value(self.slider.get_value())

class ListStore(Gtk.ListStore):
    class Columns(list):
        def __getattr__(self, name):
            try:
                return self.index(name)
            except ValueError:
                raise AttributeError(name)

        def ordered(self, valuedict):
            return [valuedict.get(key) for key in self]

    def __init__(self, **kwargs):
        GObject.GObject.__init__(self, *list(kwargs.values()))
        self.columns = ListStore.Columns(list(kwargs.keys()))

    def serialize(self):
        data = []
        for row in self:
            row_dict = {}
            for i, column in enumerate(self.columns):
                row_dict[column] = row[i]
            data.append(row_dict)
        return data

    def unserialize(self, data):
        for row in data:
            self.append(self.columns.ordered(row))


    def append(self, *args, **kwargs):
        if args:
            Gtk.ListStore.append(self, *args)
        else:
            Gtk.ListStore.append(self, self.columns.ordered(kwargs))


class ExceptionDialog(Gtk.MessageDialog):
    def __init__(self, etype, evalue, etb):
        Gtk.MessageDialog.__init__(self, buttons=Gtk.ButtonsType.CLOSE, type=Gtk.MessageType.ERROR)
        self.set_resizable(True)
        self.set_markup(_("An error has occured:\n%r\nYou should save your work and restart the application. If the error occurs again please report it to the developer." % evalue))
        import cgitb
        text = cgitb.text((etype, evalue, etb), 5)
        expander = Gtk.Expander()
        #_("Exception Details"))
        self.vbox.pack_start(expander, True, True, 0)
        textview = Gtk.TextView()
        textview.get_buffer().set_text(text)
        expander.add(scrolled(textview))
        self.show_all()

def install_exception_hook(dialog=ExceptionDialog):
    old_hook = sys.excepthook
    def new_hook(etype, evalue, etb):
        if etype not in (KeyboardInterrupt, SystemExit):
            print(etype)
            d = dialog(etype, evalue, etb)
            d.run()
            d.destroy()
        old_hook(etype, evalue, etb)
    new_hook.old_hook = old_hook
    sys.excepthook = new_hook

def install():
    """install/register all hooks provided by myGtk"""
    install_exception_hook()

def add_style_class(widget, name):
    widget.get_style_context().add_class(name)

if __name__ == "__main__":
    install_exception_hook()
    idle_do(lambda: 1/0)
    Gtk.main()
