=====================
Play it slowly Manual
=====================

About
=====
'Play it slowly' is a tool to help you when practicing or
transcribing music. It allows you to play a piece of music
at a different speed or pitch.

Package provides two applications:
 * playitslowly - UI application based on gtk
 * playitslowlycli - console application


Shortcuts
=========
The following keyboard shortcuts exist:
 * Alt + P or SPACE: Play/Pause
 * Alt + e: Rewind
 * CTRL + 1-9: Rewind (x seconds)


Selecting the audio output device
=================================
You can select which audiodevice playitslowly uses by passing
a gstreamer sink with the --sink commandline parameter.

Example:
playitslowly "--sink=alsasink device=plughw:GT10"
or
playitslowly "--sink=alsasink device=hw:1"

You can also use other sinks than alsa.


Generic Installation
====================
To install use you need to have the following libraries installed:

 * Python 2.6 (or 2.5 with simplejson installed)
 * PyGTK >= 2.10
 * PyGST >= 0.10
 * gstreamer >= 0.10 including the soundtouch/pitch element
   (included in gstreamer-plugins-bad)

Normally these libraries are already installed on your system.

To install play it slowly execute: ``python setup.py install`` as 
superuser (root). If you are using a gnome based system like Ubuntu
you can just doubleclick ``install.sh`` and select run.


Distribution Specific Installation Hints
========================================

Arch Linux
----------
(this could be obsolete by now)

Arch Linux is missing the pitch element, so you'll have to compile
yourself::

    pacman -S soundtouch
    cd /tmp
    wget gstreamer.freedesktop.org/src/gst-plugins-bad/gst-plugins-bad-0.10.9.tar.gz
    tar xzf gst-plugins-bad-0.10.9.tar.gz
    ./configure --prefix=/usr
    cd ext/soundtouch
    make && make install 

Then test if it worked::

    gst-inspect-0.10 soundtouch

Fedora
------
Install gstreamer-plugins-bad-extras

Mandriva
--------
Install gstreamer0.10-soundtouch.

Ubuntu
------
It should work out of the box!


Hacking
=======
The source code of play it slowly is hosted on github:

http://github.com/jwagner/playitslowly

If you have any questions or a patch just drop me a mail
or fill a pull request on github.


License
=======
Copyright (C) 2009 - 2011  Jonas Wagner

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


Bugreports / Questions
======================
If you encounter any bugs or have suggestions or just want to
thank me - I would like to hear about it!


Known Issues
============
* None


Contact
=======
You can reach my by e-mail: veers at gmx dot ch
