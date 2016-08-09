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

"""listener.py

Watch the Datawire Discovery's event stream to build a routing configuration for Traefik (https://traefik.io)

Usage:
    listener.py listen [options] <rules-file>
    listener.py (-h | --help)
    listener.py --version

Options:
    --debug             Enable debug mode. Debug mode enables additional logging AND runs as if in (--non-update).
    -h --help           Show the help.
    --no-update         Run in non-update mode. Traefik will not be informed of changes. [default: True]
    --version           Show the version.
"""

from docopt import docopt
from mdk_discovery import Discovery

import logging
import os
import toml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('listener')


class ApiGatewayDiscovery(Discovery):

    def __init__(self, route_manager):
        Discovery.__init__(self)
        self.route_manager = route_manager

    def _expire(self, node):
        super(ApiGatewayDiscovery, self)._expire(node)
        self.route_manager.remove_service_route(node)

    def _active(self, node):
        super(ApiGatewayDiscovery, self)._active(node)
        self.route_manager.add_service_route(node)


class RouteManager(object):

    def __init__(self, rules_file, update=True, debug=False):
        self.rules_file = rules_file
        self.debug = debug
        self.update = update
        self.frontends = {}
        self.backends = {}
        self.modified = False

    def add_frontend(self, active):
        fe_id = active.service
        fe_version = active.version  # TODO(need version awareness)
        be_id = fe_id

        if fe_id not in self.frontends:
            logger.debug("Adding new frontend (id: %s)", fe_id)
            self.frontends[fe_id] = {'backend': be_id, 'routes': {}}

        fe = self.frontends[fe_id]
        fe_routes = fe['routes']

        if 'api' not in fe_routes:
            fe_routes['api'] = {}

        fe_routes['api'] = {'rule': 'PathPrefixStrip: /{}'.format(active.service)}

    def remove_frontend(self, expire):
        fe_id = expire.service

        if fe_id not in self.backends:
            del self.frontends[fe_id]

    def add_backend(self, active):
        be_id = active.service
        props = active.properties

        if be_id not in self.backends:
            logger.debug("Adding new backend (id: %s)", be_id)
            self.backends[be_id] = {
                'LoadBalancer': {'method': 'drr'},
                'servers': {}
            }

        node_id = props['datawire_nodeId']

        be_servers = self.backends[be_id]['servers']
        be_servers[node_id] = {'url': active.address}

    def remove_backend(self, expire):
        be_id = expire.service
        props = expire.properties if expire.properties is not None else {}

        if be_id not in self.backends:
            return

        node_id = props['datawire_nodeId']
        be_servers = self.backends[be_id]['servers']

        if node_id in be_servers:
            del be_servers[node_id]

    def add_service_route(self, active):
        self.add_frontend(active)
        self.add_backend(active)
        self.modified = True
        self.write_rules()

    def remove_service_route(self, expire):
        self.remove_backend(expire)
        self.remove_frontend(expire)
        self.write_rules()

    def write_rules(self):
        if not self.modified:
            logger.debug("Routing rules not modified. Routing rules file will not be rewritten.")

        rules = {'frontends': self.frontends, 'backends':  self.backends}
        rules_toml = toml.dumps(rules)

        logger.debug("""
--- RULES DUMP (DEBUG MODE) ---
{}
--- RULES DUMP (DEBUG MODE) ---""".format(rules_toml))

        if self.update:
            with open(self.rules_file, 'w+') as f:
                f.write(rules_toml)


def listen(args):

    rules_file = args['<rules-file>']
    update = not bool(args.get('--no-update', False))

    if bool(args.get('--debug', False)):
        update = False
        logger.setLevel(logging.DEBUG)

    if update:
        logger.info("Configured to update routing rules (file: %s)", rules_file)
    else:
        logger.warn("Configured to not update routing rules. Started with (--no-update) flag.")

    routes = RouteManager(rules_file, update=update)
    disco = ApiGatewayDiscovery(routes).withToken(os.getenv("DATAWIRE_TOKEN")).connect().start()


def run_listener(args):

    if args['listen']:
        listen(args)
    else:
        exit()


def main():
    exit(run_listener(docopt(__doc__, version="listener.py {0}".format('?'))))


if __name__ == "__main__":
    main()
