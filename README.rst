===============
pytest-molecule
===============

.. image:: https://img.shields.io/pypi/v/pytest-molecule.svg
    :target: https://pypi.org/project/pytest-molecule
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-molecule.svg
    :target: https://pypi.org/project/pytest-molecule
    :alt: Python versions

.. image:: https://zuul-ci.org/gated.svg
    :target: https://dashboard.zuul.ansible.com/t/ansible/builds?project=pycontribs/selinux
    :alt: See Build Status on Zuul CI

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/python/black
    :alt: Python Black Code Style

PyTest Molecule Plugin :: auto detects and runs molecule tests

----

This plugin enables pytest discovery of all ``molecule.yml`` files inside the
codebase and runs them as pytest tests.

Once you install pytest-molecule you should be able to just run ``pytest`` in
order to run molecule on all roles and scenarios.

Optionally you can define ``MOLECULE_OPTS`` for passing extra parameters to
each molecule call.

Discovered tests do have molecule ``driver`` and ``platforms`` added as
markers_, so you can selectively limit which test types to run:

.. code-block:: shell

    # Lists all tests that uses docker
    $ pytest --collect-only -m docker

    # Runs scenarios with platform named centos7 and delegated driver:
    $ pytest -m delegated -m centos7

If the molecule scenario does not contain information about the driver, the
test associated with it gets a ``no_driver`` mark.

Please note that at this moment molecule will run the entire scenario if the
markers are platforms, this is not *yet* a way to limit which platforms are
executed inside a specific scenario.

All tests are added the ``molecule`` marker.

This plugin also adds a new pytest option named
``--molecule-unavailable-driver=skip`` which can be used to tell it what to do
when molecule drivers are not loading. Current default is ``None`` but you
can choose marks like ``skip`` or ``xfail``.

Installation
------------

You can install "pytest-molecule" via pip_ from PyPI_:

.. code-block:: shell

    $ PIP_NO_BUILD_ISOLATION=false pip install pytest-molecule

``PIP_NO_BUILD_ISOLATION`` is needed only on ancient python distributions to
workaround https://github.com/pypa/pip/issues/5229

Contributing
------------
Contributions are very welcome. Tests can be run with tox_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the MIT_ license, "pytest-molecule" is free
and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed
description.

.. _`MIT`: http://opensource.org/licenses/MIT
.. _`file an issue`: https://github.com/pycontribs/pytest-molecule/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
.. _markers: http://doc.pytest.org/en/latest/example/markers.html
