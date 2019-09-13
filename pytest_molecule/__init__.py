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

try:
    from molecule.api import drivers
except ImportError:
    # molecule<3.0
    from molecule.api import molecule_drivers as drivers


def pytest_addoption(parser):
    group = parser.getgroup("molecule")
    help_msg = (
        "What marker to add to molecule scenarios when driver is "
        "unavailable. (ex: skip, xfail)"
    )
    default = "skip"
    dest = "molecule_unavailable_driver"

    group.addoption(
        "--molecule-unavailable-driver",
        action="store",
        dest=dest,
        default=default,
        help=help_msg,
    )

    parser.addini(dest, help_msg, default=default)


def pytest_configure(config):

    config.option.molecule = {}
    for driver in drivers():
        config.addinivalue_line(
            "markers", "{0}: mark test to run only when {0} is available".format(driver)
        )
        config.option.molecule[driver] = {"available": True}
        # TODO(ssbarnea): extend molecule itself to allow it to report usable drivers
        if driver == "docker":
            try:
                import docker

                # validate docker connectivity
                # Default docker value is 60s but we want to fail faster
                # With parallel execution 5s proved to give errors.
                c = docker.from_env(timeout=10, version="auto")
                if not c.ping():
                    raise Exception("Failed to ping docker server.")

            except Exception as e:
                msg = "Molecule {} driver is not available due to: {}.".format(
                    driver, e
                )
                if config.option.molecule_unavailable_driver:
                    msg += " We will tag scenarios using it with '{}' marker.".format(
                        config.option.molecule_unavailable_driver
                    )
                logging.getLogger().warning(msg)
                config.option.molecule[driver]["available"] = False

        if driver == "delegated":
            # To protect ourselves from case where a molecule scenario using
            # `delegated` is accidentally altering the localhost on a developer
            # machine, we verify run delegated tests only when ansible `zuul`
            # or `use_for_testing` vars are defined.
            cmd = [
                "ansible",
                "localhost",
                "-e",
                "ansible_connection=local" "-o",
                "-m",
                "shell",
                "-a",
                "exit {% if zuul is defined or use_for_testing is defined %}0{% else %}1{% endif %}",
            ]
            try:
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True,
                )
                p.wait()
                if p.returncode != 0:
                    raise Exception(
                        "Error code %s returned by: %s" % (p.returncode, " ".join(cmd))
                    )
            except Exception:
                msg = "Molecule {} driver was not enabled because missing zuul.build variable in current inventory.".format(
                    driver
                )
                if config.option.molecule_unavailable_driver:
                    msg += " We will tag scenarios using it with '{}' marker.".format(
                        config.option.molecule_unavailable_driver
                    )
                logging.getLogger().warning(msg)
                config.option.molecule[driver]["available"] = False

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
        if (
            self.config.option.molecule_unavailable_driver
            and not self.config.option.molecule[self.molecule_driver]["available"]
        ):
            self.add_marker(self.config.option.molecule_unavailable_driver)

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
