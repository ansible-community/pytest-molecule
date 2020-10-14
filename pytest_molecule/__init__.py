# -*- coding: utf-8 -*-
"""pytest-molecule plugin implementation."""
# pylint: disable=protected-access
from __future__ import print_function

import logging
import os
import shlex
import subprocess
import sys
import warnings
from pipes import quote
from typing import TYPE_CHECKING, Optional

import pkg_resources
import pytest
import yaml
from molecule.api import drivers
from molecule.config import ansible_version

if TYPE_CHECKING:
    from _pytest.nodes import Node


def pytest_addoption(parser):
    """Inject new command line options to pytest."""
    group = parser.getgroup("molecule")
    help_msg = (
        "What marker to add to molecule scenarios when driver is "
        "unavailable. (ex: skip, xfail). Default: None"
    )
    default = None
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
    """Pytest hook for loading our specific configuration."""
    interesting_env_vars = [
        "ANSIBLE",
        "MOLECULE",
        "DOCKER",
        "PODMAN",
        "VAGRANT",
        "VIRSH",
        "ZUUL",
    ]

    # Add extra information that may be key for debugging failures
    for package in ["molecule"]:
        config._metadata["Packages"][package] = pkg_resources.get_distribution(
            package
        ).version

    if "Tools" not in config._metadata:
        config._metadata["Tools"] = {}
    config._metadata["Tools"]["ansible"] = str(ansible_version())

    # Adds interesting env vars
    env = ""
    for key, value in sorted(os.environ.items()):
        for var_name in interesting_env_vars:
            if key.startswith(var_name):
                env += f"{key}={value} "
    config._metadata["env"] = env

    # We hide DeprecationWarnings thrown by driver loading because these are
    # outside our control and worse: they are displayed even on projects that
    # have no molecule tests at all as pytest_configure() is called during
    # collection, causing spam.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        config.option.molecule = {}
        for driver in map(str, drivers()):
            config.addinivalue_line(
                "markers",
                "{0}: mark test to run only when {0} is available".format(driver),
            )
            config.option.molecule[driver] = {"available": True}
            if driver == "docker":
                try:
                    import docker  # pylint: disable=unused-import,import-outside-toplevel,import-error

                    # validate docker connectivity
                    # Default docker value is 60s but we want to fail faster
                    # With parallel execution 5s proved to give errors.
                    connection = docker.from_env(timeout=10, version="auto")
                    if not connection.ping():
                        raise MoleculeException("Failed to ping docker server.")

                except (ImportError, MoleculeException) as exc:
                    msg = "Molecule {} driver is not available due to: {}.".format(
                        driver, exc
                    )
                    if config.option.molecule_unavailable_driver:
                        msg += (
                            " We will tag scenarios using it with '{}' marker.".format(
                                config.option.molecule_unavailable_driver
                            )
                        )
                    logging.getLogger().warning(msg)
                    config.option.molecule[driver]["available"] = False

        config.addinivalue_line(
            "markers", "molecule: mark used by all molecule scenarios"
        )

        # validate selinux availability
        if sys.platform == "linux" and os.path.isfile("/etc/selinux/config"):
            try:
                import selinux  # noqa pylint: disable=unused-import,import-error,import-outside-toplevel
            except ImportError:
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


def pytest_collect_file(parent, path) -> Optional["Node"]:
    """Transform each found molecule.yml into a pytest test."""
    if path.basename == "molecule.yml":
        if hasattr(MoleculeFile, "from_parent"):
            return MoleculeFile.from_parent(fspath=path, parent=parent)
        return MoleculeFile(path, parent)
    return None


class MoleculeFile(pytest.File):
    """Wrapper class for molecule files."""

    def collect(self):
        """Test generator."""
        if hasattr(MoleculeItem, "from_parent"):
            yield MoleculeItem.from_parent(name="test", parent=self)
        else:
            yield MoleculeItem("test", self)

    def __str__(self):
        """Return test name string representation."""
        return str(self.fspath.relto(os.getcwd()))


class MoleculeItem(pytest.Item):
    """A molecule test.

    Pytest supports multiple tests per file, molecule only one "test".
    """

    def __init__(self, name, parent):
        """Construct MoleculeItem."""
        self.funcargs = {}
        super().__init__(name, parent)
        with open(str(self.fspath), "r") as stream:
            data = yaml.load(stream, Loader=yaml.SafeLoader)
            # we add the driver as mark
            self.molecule_driver = data["driver"]["name"]
            self.add_marker(self.molecule_driver)
            # we also add platforms as marks
            for platform in data["platforms"]:
                platform_name = platform["name"]
                self.config.addinivalue_line(
                    "markers",
                    "{0}: molecule platform name is {0}".format(platform_name),
                )
                self.add_marker(platform_name)
            self.add_marker("molecule")
            if (
                self.config.option.molecule_unavailable_driver
                and not self.config.option.molecule[self.molecule_driver]["available"]
            ):
                self.add_marker(self.config.option.molecule_unavailable_driver)

    def runtest(self):
        """Perform effective test run."""
        folders = self.fspath.dirname.split(os.sep)
        cwd = os.path.abspath(os.path.join(self.fspath.dirname, "../.."))
        scenario = folders[-1]
        # role = folders[-3]  # noqa
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

            if sys.version_info.major == 2:
                # https://bugs.python.org/issue13202
                proc = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                )
                for line in proc.stdout:
                    print(line, end="")
                proc.wait()
                if proc.returncode != 0:
                    pytest.fail(
                        "Error code %s returned by: %s"
                        % (proc.returncode, " ".join(cmd)),
                        pytrace=False,
                    )
            else:
                with subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                ) as proc:
                    for line in proc.stdout:
                        print(line, end="")
                    proc.wait()
                    if proc.returncode != 0:
                        pytest.fail(
                            "Error code %s returned by: %s"
                            % (proc.returncode, " ".join(cmd)),
                            pytrace=False,
                        )
        except Exception as exc:  # pylint: disable=broad-except
            pytest.fail(
                "Exception %s returned by: %s" % (exc, " ".join(cmd)), pytrace=False
            )

    def reportinfo(self):
        """Return representation of test location when in verbose mode."""
        return self.fspath, 0, "usecase: %s" % self.name

    def __str__(self):
        """Return name of the test."""
        return "{}[{}]".format(self.name, self.molecule_driver)


class MoleculeException(Exception):
    """Custom exception for error reporting."""
