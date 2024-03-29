#!/usr/bin/env python3
import os

from setuptools import setup


install_requires = [
    'click',
    'event',
    'flask'
]

setup(name='titus-isolate',
      description='Isolate containers running on Titus',
      maintainer="Gabriel Hartmann",
      maintainer_email="ghartmann@netflix.com",
      version=os.getenv("TITUS_ISOLATE_VERSION", "0.SNAPSHOT"),
      packages=[
          "titus_isolate",
          "titus_isolate/allocate",
          "titus_isolate/allocate/remote",
          "titus_isolate/api",
          "titus_isolate/cgroup",
          "titus_isolate/crd",
          "titus_isolate/crd/model",
          "titus_isolate/crd/publish",
          "titus_isolate/config",
          "titus_isolate/event",
          "titus_isolate/isolate",
          "titus_isolate/metrics",
          "titus_isolate/model",
          "titus_isolate/model/processor",
          "titus_isolate/monitor",
          "titus_isolate/numa",
          "titus_isolate/pod",
          "titus_isolate/predict",
          "titus_isolate/kub"],
      url="https://github.com/Netflix-Skunkworks/titus-isolate")
