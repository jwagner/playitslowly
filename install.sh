#!/bin/sh
gksu -u root -- python setup.py install --prefix=/usr
zenity --info --text "'Play it slowly' has been installed"
