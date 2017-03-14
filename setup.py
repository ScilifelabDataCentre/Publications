#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(name='PubBase',
      version='0.1',
      description='Simple publication reference database with web interface.',
      license='MIT',
      author='Per Kraulis',
      author_email='per.kraulis@scilifelab.se',
      url='https://github.com/pekrau/PubBase',
      packages = find_packages(),
      install_requires=['tornado']
     )
