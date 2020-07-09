#!/bin/bash
set -euxo pipefail
# Used by Zuul CI to perform extra bootstrapping
sudo python3 -m pip install 'tox>=3.16.1'
