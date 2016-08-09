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
from mdk_runtime import defaultRuntime, Schedule, Happening
from mdk import init

import logging
import os
import toml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('listener')


class ApiGatewayDiscovery(Discovery):

    def __init__(self, runtime, route_manager):
        Discovery.__init__(self, runtime)
        self.route_manager = route_manager

    def _expire(self, node):
        super(ApiGatewayDiscovery, self)._expire(node)
        self.route_manager.remove_service_route(node)

    def _active(self, node):
        super(ApiGatewayDiscovery, self)._active(node)
        self.route_manager.add_service_route(node)


class RouteManager(object):

    _EMPTY_RULES_TOML = """
[frontends]

[backends]
"""

    def __init__(self, scheduler, scheduler_delay, rules_file, update=True, debug=False):
        self.scheduler = scheduler
        self.scheduler_delay = int(scheduler_delay)
        self.rules_file = rules_file
        self.debug = debug
        self.update = update
        self.frontends = {}
        self.backends = {}
        self.modified = False

    def _schedule_flush(self):
        self.dispatcher.tell(self, Schedule("rules:flush", self.scheduler_delay), self.scheduler)

    def onStart(self, dispatcher):
        self.dispatcher = dispatcher
        self._schedule_flush()

    def onMessage(self, origin, message):
        if isinstance(message, Happening) and message.event == "rules:flush":
            self.write_rules()
            self._schedule_flush()

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
        props = active.properties if active.properties is not None else {}

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
            if len(be_servers) == 0:
                del self.backends[be_id]

    def add_service_route(self, active):
        self.add_frontend(active)
        self.add_backend(active)
        self.modified = True

    def remove_service_route(self, expire):
        self.remove_backend(expire)
        self.remove_frontend(expire)
        self.modified = True

    def write_rules(self):
        if self.modified:
            logger.info("Routing rules modified. Routing rules file will be rewritten.")

            # The below code creates the appropriate dictionary structure for the Traefik routing file. However, there
            # is an issue and I do not know whether it is related to the Python's TOML emitter, Traefik's Go TOML parser
            # or an issue with the TOML specification I do not clearly understand.
            #
            # The situation is this:
            # ----------------------
            #
            #   1. Traefik can have zero routes in it (default state).
            #   2. Traefik expects that the routes file be "well-formed" and contain "frontends" and "backends"
            #      sections regardless of whether they are empty (no routes) or populated (some routes).
            #   3. The Python TOML library interprets Python dictionary {'frontends': {}, 'backends': {}} as empty and
            #      emits TOML that looks like this " ".
            #   4. The Python TOML library seems incorrect. I would expect the serialized form to be near equivalent to
            #
            #        """
            #        [frontends]
            #
            #        [backends]
            #
            #        """
            #
            #   5. The Traefik Go TOML parser does not accept empty nothingness OR the Traefik server decides a blank
            #      file is invalid and does not reload.
            #   6. Because Traefik does not reload then old routes stay in the server when a situation where ALL
            #      [frontends] and [backends] are removed.
            #
            # Resolution:
            # ----------
            #
            #   1. When there are no frontends or backends to emit (the {'frontends': {}, 'backends': {}} case) then
            #      the program should output the statically defined string described above in <4>.
            #   2. When there are frontends or backends to emit then the Python TOML library should be used.
            #
            # Hooray for stupid esoteric configuration formats!
            #
            rules = {'frontends': self.frontends, 'backends':  self.backends}
            rules_toml = RouteManager._EMPTY_RULES_TOML
            if rules != {'frontends': {}, 'backends': {}}:
                rules_toml = toml.dumps(rules)

            if self.update:
                with open(self.rules_file, 'w+') as f:
                    f.write(rules_toml)
        else:
            logger.info("Routing rules not modified. Routing rules file will not be rewritten.")


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

    mdk = init()
    mdk_runtime = defaultRuntime()

    routes = RouteManager(mdk_runtime.getScheduleService(), 5, rules_file, update=update)
    mdk_runtime.dispatcher.startActor(routes)

    mdk._disco = ApiGatewayDiscovery(mdk_runtime, routes).withToken(os.getenv("DATAWIRE_TOKEN")).connect().start()
    mdk.start()


def run_listener(args):

    if args['listen']:
        listen(args)
    else:
        exit()


def main():
    exit(run_listener(docopt(__doc__, version="listener.py {0}".format('?'))))


if __name__ == "__main__":
    main()
