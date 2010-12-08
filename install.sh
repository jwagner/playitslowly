#!/bin/sh
gksu -u root -- python setup.py install
zenity --info --text "'Play it slowly' has been installed"
