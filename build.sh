#!/bin/bash -x
set -euo pipefail
DERIVED_VERSION=$(date +%Y%m%d).$(git describe --tags --long | sed s/-/./g)
TITUS_ISOLATE_VERSION=$(git describe --exact-match --tags || echo $DERIVED_VERSION)

echo "Fetching git tags"
git fetch --tags
git describe --tags

echo "Building build docker image"
docker build -t deb release

echo "Building version ${TITUS_ISOLATE_VERSION}"
docker run --rm -e TITUS_ISOLATE_VERSION=${TITUS_ISOLATE_VERSION} -v $PWD:/src deb:latest
mv *.deb titus-isolate_latest.deb
