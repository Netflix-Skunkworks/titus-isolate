"""Example Python application, using the paved path."""

from setuptools import setup


setup(
    name='titus_isolate',
    versioning='build-id',
    author='titus',
    author_email='titus-ops@netflix.com',
    keywords='titus_isolate',
    url='https://stash.corp.netflix.com/projects/TN/repos/titus_isolate/browse',
    setup_requires=['setupmeta'],
    python_requires='>=2.7',
    install_requires=[],
    extras_require={
        'test': ['tox'],
    },
)
