# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
import os
import pytest
import subprocess
import sys


def pytest_configure(config):

    import docker

    # validate docker conectivity
    c = docker.from_env(timeout=5, version="auto")
    if not c.ping():
        raise Exception("Failed to ping docker server.")

    # validate selinux availability
    if sys.platform == 'linux':
        try:
            import selinux  # noqa
        except Exception as e:
            logging.error(
                "It appears that you are trying to use "
                "molecule with a Python interpreter that does not have the "
                "libselinux python bindings installed. These can only be "
                "installed using your distro package manager and are specific "
                "to each python version. Common package names: "
                "libselinux-python python2-libselinux python3-libselinux")
            raise e


def pytest_collect_file(parent, path):
    if path.basename == "molecule.yml":
        return MoleculeFile(path, parent)


class MoleculeFile(pytest.File):
    def collect(self):
        yield MoleculeItem("", self)


class MoleculeItem(pytest.Item):
    def __init__(self, name, parent):
        super(MoleculeItem, self).__init__(name, parent)

    def runtest(self):
        folders = self.fspath.dirname.split(os.sep)
        cwd = os.path.abspath(os.path.join(self.fspath.dirname, '../..'))
        scenario = folders[-1]
        role = folders[-3]  # noqa

        cmd = ['python', '-m', 'molecule', 'test', '-s', scenario]
        print("running: %s (from %s)" % (" " .join(cmd), cwd))
        # Workaround for STDOUT/STDERR line ordering issue:
        # https://github.com/pytest-dev/pytest/issues/5449
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True)
        for line in p.stdout:
            print(line, end="")
        p.wait()
        assert p.returncode == 0


class MoleculeException(Exception):
    """ custom exception for error reporting. """
