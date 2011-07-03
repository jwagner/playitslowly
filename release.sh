#!/bin/sh
rm dist/*
python setup.py sdist
sudo make builddeb
cp ../playitslowly_*.deb dist
#sudo rm ../playitslowly_*
rsync -vrt --copy-links dist/* 29a.ch:/var/www/29a.ch/playitslowly/

