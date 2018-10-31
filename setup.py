#!/usr/bin/env python3
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
      version='0.1',
      packages=["titus_isolate", "titus_isolate/api", "titus_isolate/docker", "titus_isolate/isolate",
                "titus_isolate/model", "titus_isolate/model/processor"],
      scripts=["startup/main.py"],
      url="https://github.com/Netflix-Skunkworks/titus-isolate"
      )
