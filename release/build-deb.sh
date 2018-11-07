#!/bin/bash
set -e
echo "Removing old tox files"
rm -rf .tox

echo "Removing old debs"
rm -f *.deb

echo "Removing dist directory"
rm -rf dist

echo "Removing virtualenv (env)"
rm -rf env

echo "Setting up virtualenv (env)"
virtualenv --python=/usr/bin/python3 env

echo "Activating virtualenv (env)"
. env/bin/activate

echo "Appending special requirements to requirements.txt"
cp /src/requirements.txt /src/req.txt
echo systemd >> /src/requirements.txt

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
cp /rules debian/

echo "Adding systemd unit file"
cp /titus-isolate.service debian/

echo "Adding systemd preinst override file"
cp /titus-isolate.preinst debian/

echo "Building debian package"
dpkg-buildpackage -us -uc

echo "Copying debian package to host"
cd ..
cp *.deb ../

echo "Deactivating virtualenv (env)"
deactivate

echo "Removing virtualenv (env)"
rm -rf env

echo "Restoring requirements.txt"
mv /src/req.txt /src/requirements.txt
