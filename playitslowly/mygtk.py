"""
Author: Jonas Wagner

Play it slowly
Copyright (C) 2009 Jonas Wagner

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

import gtk, gobject
import math
import sys
from datetime import timedelta

_ = lambda s: s

buttons_ok_cancel = (gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OPEN,gtk.RESPONSE_OK)
class FileChooserDialog(gtk.FileChooserDialog):
    """a file chooser dialog which automatically sets the correct buttons!"""
    def __init__(self, title=None, parent=None, action=None):
        if action == gtk.FILE_CHOOSER_ACTION_SAVE:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE ,gtk.RESPONSE_OK)
            title = title or _(u"Save File")
        else:
            if action == gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER:
                title = title or _(u"Select Folder")
            elif action == gtk.FILE_CHOOSER_ACTION_CREATE_FOLDER:
                title = title or _(u"Create Folder")
            else:
                title = title or _(u"Open a File")
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN ,gtk.RESPONSE_OK)
        gtk.FileChooserDialog.__init__(self, title, parent, action, buttons)

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
            except gobject.GError, e:
                #logger.exception("Unable to load icon %r probably your "
                #        "icon theme isn't conforming to the icon naming "
                #        "convention. You might want to try the tango icon "
                #        "theme", name)
                return None
        return self.cache[(name, size)]

    def get_image(self, name, size):
        pixbuf = self.get_icon(name, size)
        img = gtk.Image()
        img.set_from_pixbuf(pixbuf)
        return img

    def has_icon(self, name):
        return self.icon_theme.has_icon(name)

icon_theme = gtk.icon_theme_get_default()
iconfactory = IconFactory(icon_theme)

def idle_do(func, *args):
    """wrapper arround idle_add that will always run once"""
    def wrapper(*args):
        # throw away the result of the function!
        func(*args)
    gobject.idle_add(wrapper, *args)

def scrolled(widget, shadow=gtk.SHADOW_NONE):
    window = gtk.ScrolledWindow()
    window.set_shadow_type(shadow)
    window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    if widget.set_scroll_adjustments(window.get_hadjustment(),
                                      window.get_vadjustment()):
        window.add(widget)
    else:
        window.add_with_viewport(widget)
    return window


def make_table(widgets):
    """return a gtk.Table containing all the widgets"""
    columns = max(map(len, widgets))
    table = gtk.Table(len(widgets), columns, False)
    for y, row in enumerate(widgets):
        for x, widget in enumerate(row):
            if widget:
                table.attach(widget, x, x+1, y, y+1,
                        xoptions=gtk.EXPAND|gtk.FILL, xpadding=4, ypadding=4)
    return table

def register_webbrowser_url_hook():
    """registers pythons webbrowser module as url_hook"""
    import webbrowser
    def open_url(d, link, data):
        webbrowser.open(link)
    if sys.platform.startswith("linux"):
        webbrowser.register("xdg-open", None,
                webbrowser.GenericBrowser('xdg-open'),  update_tryorder=-1)
    gtk.about_dialog_set_url_hook(open_url, None)

class gtklock:
    """A context manger for the gtk.gdk.threads_*

    can be used like this
    >> with gtklock:
    >>     pass
    """
    @staticmethod
    def __enter__():
        gtk.gdk.threads_enter()

    @staticmethod
    def __exit__(*args):
        gtk.gdk.threads_leave()

def gtk_yield():
    """process all the peding events in the mainloop"""
    while gtk.events_pending():
         gtk.main_iteration()

class IconButton(gtk.Button):
    def __init__(self, icon, size=None, label=None):
        gtk.Button.__init__(self)
        self.size = size or gtk.ICON_SIZE_BUTTON
        self.hbox = gtk.HBox()
        self.add(self.hbox)
        self.img = None
        self.set_icon(icon)
        self.label = None
        self.set_label(label)

    def set_label(self, label):
        if self.label:
            self.label.set_text(label)
        else:
            self.label = gtk.Label(label)
            self.hbox.pack_end(self.label)

    def set_icon(self, icon):
        if self.img:
            self.img.set_from_pixbuf(iconfactory.get_icon(icon, self.size))
        else:
            self.img = iconfactory.get_image(icon, self.size)
            self.hbox.pack_start(self.img)
        self._icon = icon
    icon = property(lambda self: self._icon, set_icon)

class IconMenuItem(gtk.ImageMenuItem):
    icon_size = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)[0]
    def __init__(self, icon, text):
        gtk.ImageMenuItem.__init__(self)
        self.set_image(iconfactory.get_image(icon, self.icon_size))
        label = gtk.Label(text)
        label.set_alignment(0.0, 0.5)
        self.add(label)
        self.show_all()

def show_error(msg):
    """Show a 'nice' errbox"""
    dialog = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, message_format=str(msg),
            buttons=gtk.BUTTONS_OK)
    dialog.set_title(_("Error"))
    # dialog.run() - this breaks when called from gobject.idle_add
    # dialog.hide()
    # dialog.destroy
    dialog.show()
    dialog.connect("response", lambda dialog, response: dialog.destroy())
    return dialog

def make_menu(entries, menu):
    for entry in entries:
        if entry is None:
            sub = None
            item = gtk.SeparatorMenuItem()
        else:
            key, sub = entry
            if isinstance(key, tuple):
                item = IconMenuItem(*key)
            elif key.startswith("gtk-"):
                item = gtk.ImageMenuItem(stock_id=key)
            else:
                item = gtk.MenuItem(key)
        if sub:
            if callable(sub):
                item.connect("activate", sub)
            else:
                submenu = gtk.Menu()
                item.set_submenu(submenu)
                make_menu(sub, submenu)
        menu.append(item)

def form(rows):
    table = gtk.Table(len(rows), 2, False)
    for y, (text, widget) in enumerate(rows):
        label = gtk.Label(text)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, y, y+1, xoptions=gtk.SHRINK|gtk.FILL, xpadding=4)
        table.attach(widget, 1, 2, y, y+1, xoptions=gtk.EXPAND|gtk.FILL, xpadding=4)
    return table

def make_table(widgets):
    """return a gtk.Table containing all the widgets"""
    columns = max(map(len, widgets))
    table = gtk.Table(len(widgets), columns, False)
    for y, row in enumerate(widgets):
        for x, widget in enumerate(row):
            table.attach(widget, x, x+1, y, y+1, xoptions=gtk.EXPAND|gtk.FILL,
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

class VScale(gtk.VScale, Scale):
    def __init__(self, *args):
        gtk.VScale.__init__(self, *args)
        Scale.__init__(self)

class HScale(gtk.HScale, Scale):
    def __init__(self, *args):
        gtk.HScale.__init__(self, *args)
        Scale.__init__(self)

class ClockScale(gtk.VBox):
    def __init__(self, *args):
        gtk.VBox.__init__(self)
        self.clocklabel = gtk.Label()
        # slider
        self.scale = HScale(*args)
        self.scale.set_draw_value(False)
        self.set_value = self.scale.set_value
        self.get_value = self.scale.get_value
        self.get_adjustment = self.scale.get_adjustment
        self.set_adjustment = self.scale.set_adjustment
        self.set_range = self.scale.set_range

        self.update_clock()
        self.scale.connect("value-changed", self.update_clock)

        self.pack_start(self.clocklabel) #, True, True)
        self.pack_start(self.scale) #, True, True)
    def update_clock(self, sender=None):
        self.clocklabel.set_markup(self.format(self.get_value()))
    def format(self, value):
        ms = str(timedelta(seconds=value))[8:11]
        value = str(timedelta(seconds=value))[:7]
        if ms == '':
            ms = '000'
        return '<span size="large" weight="bold">%s<span size="medium">.%s</span></span>' % (value, ms)

class TextScale(gtk.HBox):
    format = "%.2f"
    size = 6
    def __init__(self, *args):
        gtk.HBox.__init__(self)
        self.from_text = False

        self.entry = gtk.Entry()

        self.scale = HScale(*args)
        self.scale.set_draw_value(False)
        self.set_value = self.scale.set_value
        self.get_value = self.scale.get_value
        self.get_adjustment = self.scale.get_adjustment
        self.set_adjustment = self.scale.set_adjustment
        self.set_range = self.scale.set_range

        #n = len(self.format % self.scale.get_adjustment().get_upper())
        self.entry.set_width_chars(self.size)

        self.update_text()
        self.scale.connect("value-changed", self.update_text)
        self.entry.connect("changed", self.update_scale)

        self.pack_start(self.scale, True, True)
        self.pack_start(self.entry, False, False)

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

# TODO: substitute for a decorator?
class TextScaleReset(TextScale):
    def __init__(self, *args):
        TextScale.__init__(self, *args)
        self.reset_button = gtk.Button(_('Reset'))
        self.reset_button.connect("clicked", self.reset_to_default)
        self.pack_start(self.reset_button, False, False)
        self.reorder_child(self.reset_button, 1)
        self.default_value = self.get_value()
	self.add_accelerator = self.reset_button.add_accelerator
    def reset_to_default(self, sender=None):
        self.set_value(self.default_value)

# TODO: substitute for a decorator?
class TextScaleWithCurPos(TextScale):
    def __init__(self, slider, *args):
        TextScale.__init__(self, *args)
        self.now_button = gtk.Button(_('Now!'))
        self.now_button.connect("clicked", self.update_to_current_position)
        self.pack_start(self.now_button, False, False)
        self.reorder_child(self.now_button, 1)
        self.slider = slider
	self.add_accelerator = self.now_button.add_accelerator
    def update_to_current_position(self, sender=None):
        self.set_value(self.slider.get_value())

class ListStore(gtk.ListStore):
    class Columns(list):
        def __getattr__(self, name):
            try:
                return self.index(name)
            except ValueError:
                raise AttributeError, name

        def ordered(self, valuedict):
            return [valuedict.get(key) for key in self]

    def __init__(self, **kwargs):
        gtk.ListStore.__init__(self, *kwargs.values())
        self.columns = ListStore.Columns(kwargs.keys())

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
            gtk.ListStore.append(self, *args)
        else:
            gtk.ListStore.append(self, self.columns.ordered(kwargs))


class ExceptionDialog(gtk.MessageDialog):
    def __init__(self, etype, evalue, etb):
        gtk.MessageDialog.__init__(self, buttons=gtk.BUTTONS_CLOSE, type=gtk.MESSAGE_ERROR)
        self.set_resizable(True)
        self.set_markup(_("An error has occured:\n%r\nYou should save your work and restart the application. If the error occurs again please report it to the developer." % evalue))
        import cgitb
        text = cgitb.text((etype, evalue, etb), 5)
        expander = gtk.Expander(_("Exception Details"))
        self.vbox.pack_start(expander)
        textview = gtk.TextView()
        textview.get_buffer().set_text(text)
        expander.add(scrolled(textview))
        self.show_all()

def install_exception_hook(dialog=ExceptionDialog):
    old_hook = sys.excepthook
    def new_hook(etype, evalue, etb):
        if etype not in (KeyboardInterrupt, SystemExit):
            d = dialog(etype, evalue, etb)
            d.run()
            d.destroy()
        old_hook(etype, evalue, etb)
    new_hook.old_hook = old_hook
    sys.excepthook = new_hook

def install():
    """install/register all hooks provided by mygtk"""
    install_exception_hook()
    register_webbrowser_url_hook()

if __name__ == "__main__":
    install_exception_hook()
    idle_do(lambda: 1/0)
    gtk.main()
