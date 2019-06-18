# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import pytest
import subprocess


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
