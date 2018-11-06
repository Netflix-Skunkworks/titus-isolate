#!/usr/bin/env python3
import os

from distutils.core import setup

install_requires = [
    'click',
    'docker',
    'flask'
]

setup(name='titus-isolate',
      description='Isolate containers running on Titus',
      maintainer="Gabriel Hartmann",
      maintainer_email="ghartmann@netflix.com",
      version=os.getenv("TITUS_ISOLATE_VERSION", "0.SNAPSHOT"),
      packages=["titus_isolate", "titus_isolate/api", "titus_isolate/docker", "titus_isolate/isolate",
                "titus_isolate/metrics", "titus_isolate/model", "titus_isolate/model/processor"],
      scripts=["startup/titus-isolate"],
      url="https://github.com/Netflix-Skunkworks/titus-isolate"
      )
