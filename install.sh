#!/bin/bash
CWD=`pwd`
pkexec bash -c "cd $CWD && python3 setup.py install && desktop-file-install /usr/local/share/applications/playitslowly.desktop"
zenity --info --text "'Play it Slowly' has been installed"
