#!/bin/bash
set -e

echo "Removing dist directory"
rm -rf dist

echo "Setting up virtualenv (env)"
virtualenv env

echo "Activating virutalenv (env)"
. env/bin/activate

echo "Creating source distribution"
python3 setup.py sdist

echo "Moving to dist directory"
cd dist

echo "Untarring source distribution"
tar -xzmf *

echo "Moving to untarred directory"
cd */

echo "Creating debian directory"
DEBEMAIL=titusops@netflix.com debmake -b':py3'

echo "Overwriting rules file"
cp /rules debian/rules

echo "Building debian package"
dpkg-buildpackage -us -uc

echo "Copying debian package to host"
cd ..
cp *.deb ../
