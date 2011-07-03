#!/bin/sh
python setup.py sdist
rsync -vrt --copy-links dist/* 29a.ch:/var/www/29a.ch/playitslowly/

