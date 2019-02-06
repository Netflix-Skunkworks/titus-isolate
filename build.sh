#!/bin/bash -x
set -euo pipefail
export TITUS_ISOLATE_VERSION=$(date +%Y%m%d).$(git describe --tags --long | sed s/-/./g)
echo "Building version ${TITUS_ISOLATE_VERSION}"
docker run --rm -e TITUS_ISOLATE_VERSION=${TITUS_ISOLATE_VERSION} -v $PWD:/src deb:latest
mv *.deb titus-isolate_latest.deb

