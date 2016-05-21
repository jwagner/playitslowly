#!/usr/bin/env python
import sys
import os

from distutils.core import setup
from distutils.command.install import install, write_file
from distutils.command.install_egg_info import to_filename, safe_name
from functools import reduce

class new_install(install):
    def initialize_options(self):
        install.initialize_options(self)

    def run(self):
        install.run(self)
        # hack to remove old module
        old_path = os.path.join(self.install_libbase, "playitslowly", "playitslowly.py")
        for p in (old_path + x for x in ("o", "c", "")):
            if os.path.exists(p):
                self.execute(os.unlink, (p, ), "Removing old file %r" % p)

        # write install-info
        basename = "%s-py%s.install-info" % (
            to_filename(safe_name(self.distribution.get_name())),
            sys.version[:3]
        )
        install_info = os.path.join(self.install_libbase, basename)
        outputs = self.get_outputs()
        if self.root:               # strip any package prefix
            root_len = len(self.root)
            for counter in range(len(outputs)):
                outputs[counter] = outputs[counter][root_len:]
        self.execute(write_file,
                (install_info, outputs),
                "writing install-info to '%s'" % install_info)

def ls_r(dir):
    def do_reduce(a, b):
        files = []
        for f in b[2]:
            files.append(os.path.join(b[0], f))
        a.append((b[0], files))
        return a
    return reduce(do_reduce, os.walk(dir), [])

kwargs = {
      'cmdclass': {'install': new_install},
      'name': 'playitslowly',
      'version': "1.5.1",
      'description': 'A tool to help you when transcribing music. It allows you to play a piece of music at a different speed or pitch.',
      'author': 'Jonas Wagner',
      'author_email': 'jonas@29a.ch',
      'url': 'http://29a.ch/playitslowly/',
      'packages': ['playitslowly'],
      'scripts': ['bin/playitslowly'],
      'options': {'py2exe':{
          'packages': 'encodings',
          'includes': 'cairo, pango, pangocairo, atk, gobject',
          'dist_dir': 'dist/win32',
          'optimize': 2,
          }},
      'data_files': ls_r('share'),
      'license': 'GNU GPL v3',
      'classifiers': [
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        ]
}

try:
    import py2exe
    kwargs['windows'] = [{'script': 'bin/playitslowly',
          'icon_resources': [(1, 'playitslowly.ico')],
          'dest_base': 'playitslowly'}]
except ImportError:
    pass

setup(**kwargs)
