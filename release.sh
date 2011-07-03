#!/bin/sh
rm dist/*
sudo make builddeb
cp ../playitslowly_*.deb dist
sudo rm ../playitslowly_*
python setup.py sdist
rsync -vrt --copy-links dist/* 29a.ch:/var/www/29a.ch/playitslowly/

