# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
import os
import pytest
import subprocess
import shlex
import sys
from pipes import quote
import yaml


def pytest_configure(config):

    # TODO(ssbarnea): Replace this an API call once molecule implements it
    # https://github.com/ansible/molecule/issues/2213
    drivers = [
        "azure",
        "delegated",
        "docker",
        "ec2",
        "gce",
        "hetznercloud",
        "linode",
        "lxc",
        "lxd",
        "openstack",
        "vagrant",
    ]
    for driver in drivers:
        config.addinivalue_line(
            "markers", "{0}: mark test to run only when {0} is available".format(driver)
        )
    config.addinivalue_line("markers", "molecule: mark used by all molecule scenarios")

    # validate selinux availability
    if sys.platform == "linux" and os.path.isfile("/etc/selinux/config"):
        try:
            import selinux  # noqa
        except Exception:
            logging.error(
                "It appears that you are trying to use "
                "molecule with a Python interpreter that does not have the "
                "libselinux python bindings installed. These can only be "
                "installed using your distro package manager and are specific "
                "to each python version. Common package names: "
                "libselinux-python python2-libselinux python3-libselinux"
            )
            # we do not re-raise this exception because missing or broken
            # selinux bindings are not guaranteed to fail molecule execution.


def pytest_collect_file(parent, path):
    if path.basename == "molecule.yml":
        return MoleculeFile(path, parent)


class MoleculeFile(pytest.File):
    def collect(self):
        yield MoleculeItem("test", self)

    def __str__(self):
        return str(self.fspath.relto(os.getcwd()))


class MoleculeItem(pytest.Item):
    def __init__(self, name, parent):
        super(MoleculeItem, self).__init__(name, parent)
        stream = open(str(self.fspath), "r")
        data = yaml.load(stream, Loader=yaml.SafeLoader)
        # we add the driver as mark
        self.molecule_driver = data["driver"]["name"]
        self.add_marker(self.molecule_driver)
        # we also add platforms as marks
        for x in data["platforms"]:
            p = x["name"]
            self.config.addinivalue_line(
                "markers", "{0}: molecule platform name is {0}".format(p)
            )
            self.add_marker(p)
        self.add_marker("molecule")

    def runtest(self):
        folders = self.fspath.dirname.split(os.sep)
        cwd = os.path.abspath(os.path.join(self.fspath.dirname, "../.."))
        scenario = folders[-1]
        role = folders[-3]  # noqa
        cmd = [sys.executable, "-m", "molecule", self.name, "-s", scenario]

        # We append the additional options to molecule call, allowing user to
        # control how molecule is called by pytest-molecule
        opts = os.environ.get("MOLECULE_OPTS")
        if opts:
            cmd.extend(shlex.split(opts))

        print("running: %s (from %s)" % (" ".join(quote(arg) for arg in cmd), cwd))

        try:
            # Workaround for STDOUT/STDERR line ordering issue:
            # https://github.com/pytest-dev/pytest/issues/5449
            p = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            )
            for line in p.stdout:
                print(line, end="")
            p.wait()
            if p.returncode != 0:
                pytest.fail(
                    "Error code %s returned by: %s" % (p.returncode, " ".join(cmd)),
                    pytrace=False,
                )
        except Exception as e:
            pytest.fail(
                "Exception %s returned by: %s" % (e, " ".join(cmd)), pytrace=False
            )

    def reportinfo(self):
        return self.fspath, 0, "usecase: %s" % self.name

    def __str__(self):
        return "{}[{}]".format(self.name, self.molecule_driver)


class MoleculeException(Exception):
    """ custom exception for error reporting. """
