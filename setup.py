#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import codecs
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


setup(
    name='pytest-molecule',
    version='0.2.2',
    author='Sorin Sbarnea',
    author_email='sorin.sbarnea@gmail.com',
    maintainer='Sorin Sbarnea',
    maintainer_email='sorin.sbarnea@gmail.com',
    license='MIT',
    url='https://github.com/pycontribs/pytest-molecule',
    description='PyTest Molecule Plugin :: discover and run molecule tests',
    long_description=read('README.rst'),
    py_modules=['pytest_molecule'],
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
    install_requires=['pytest>=3.5.0', 'molecule>=2.22rc1'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points={
        'pytest11': [
            'molecule = pytest_molecule',
        ],
    },
)
