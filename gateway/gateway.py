#!/usr/bin/env python

# Copyright 2015, 2016 Datawire. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""gateway.py

Watch the Datawire Discovery's event stream to build a routing configuration for Traefik (https://traefik.io)

Usage:
    gateway listen <route-file>
    gateway (-h | --help)
    gateway --version

Options:
    -h --help           Show the help.
    --no-update         Run in non-update mode. Traefik will not be informed of changes.
    --version           Show the version.
"""

from docopt import docopt

import mdk as datawire_mdk

no_update = False


def listen(args):

    mdk = datawire_mdk.init()
    mdk.start()


def run_gateway(args):
    if args['--no-update']:
        global no_update
        no_update = True

    if args['listen']:
        listen(args)
    else:
        exit()


def main():
    exit(run_gateway(docopt(__doc__, version="gateway {0}".format('?'))))


if __name__ == "__main__":
    main()
