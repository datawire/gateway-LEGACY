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
    listener.py listen [options]
    listener.py (-h | --help)
    listener.py --version

Options:
    --debug                 Enable debug mode. Debug mode enables additional logging AND runs as if in (--no-update).
    -h --help               Show the help.
    --no-update             Run in non-update mode. Traefik will not be informed of changes. [default: True]
    --traefik-addr=<addr>   The Traefik server address [default: localhost:8000]
    --version               Show the version.
"""

from docopt import docopt
from mdk_discovery import NodeActive, NodeExpired, CircuitBreakerFactory
from mdk_runtime import defaultRuntime, Schedule, Happening
from traefik import TraefikClient

from gateway import log_format
import logging
import mdk_discovery
import os
import sys

from pythonjsonlogger import jsonlogger

logger = logging.getLogger('listener')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(log_format)
handler.setFormatter(formatter)
logger.addHandler(handler)


class RouteManager(object):

    def __init__(self, traefik_client, update=True):
        if not isinstance(traefik_client, TraefikClient):
            raise ValueError("traefik_client is not a valid instance of TraefikClient")

        self.dispatcher = None
        self._traefik = traefik_client
        self.frontends = {}
        self.backends = {}
        self._update = bool(update)

    def onStart(self, dispatcher):
        self.dispatcher = dispatcher

    def onMessage(self, origin, message):
        if isinstance(message, NodeActive) or isinstance(message, NodeExpired):
            if isinstance(message, NodeActive):
                self.__upsert_frontend(message)
                self.__upsert_backend(message)
            elif isinstance(message, NodeExpired):
                self.__remove_frontend(message)
                self.__remove_backend(message)

            self.__reconfigure()


    def __reconfigure(self):
        routes = {'frontends': self.frontends, 'backends': self.backends}
        if self._update:
            logger.debug("Reconfiguring Traefik",
                         extra={'frontends_count': len(self.frontends), 'backends_count': len(self.backends)})

            self._traefik.reconfigure(routes)

    def __upsert_frontend(self, active):
        node = active.node

        fe_id = node.service
        fe_version = node.version  # TODO(need version awareness)
        be_id = fe_id

        if fe_id not in self.frontends:
            logger.info("Adding new frontend (id: %s)", fe_id)
            self.frontends[fe_id] = {'backend': be_id, 'routes': {}}

        fe = self.frontends[fe_id]
        fe_routes = fe['routes']

        if 'api' not in fe_routes:
            fe_routes['api'] = {}

        fe_routes['api'] = {'rule': 'PathPrefixStrip: /{}'.format(node.service)}

    def __remove_frontend(self, expire):
        node = expire.node

        fe_id = node.service

        if fe_id in self.frontends:
            logger.info("Removing frontend (id: %s)", fe_id)
            del self.frontends[fe_id]

    def __upsert_backend(self, active):
        node = active.node
        be_id = node.service
        props = node.properties if node.properties is not None else {}

        if be_id not in self.backends:
            logger.info("Adding new backend (id: %s)", be_id)
            self.backends[be_id] = {
                'LoadBalancer': {'method': 'drr'},
                'servers': {}
            }

        node_id = props['datawire_nodeId']

        be_servers = self.backends[be_id]['servers']
        be_servers[node_id] = {'url': node.address}

    def __remove_backend(self, expire):
        node = expire.node
        be_id = node.service
        props = node.properties if node.properties is not None else {}

        if be_id in self.backends:
            logger.info("Removing backend (id: %s)", be_id)
            node_id = props['datawire_nodeId']
            be_servers = self.backends[be_id]['servers']

            if node_id in be_servers:
                del be_servers[node_id]
                if len(be_servers) == 0:
                    del self.backends[be_id]


def listen(args):

    update = not bool(args.get('--no-update', False))

    if bool(args.get('--debug', False)):
        update = False
        logger.setLevel(logging.DEBUG)

    if update:
        logger.info("Configured to update routing rules.")
    else:
        logger.warn("Configured to not update routing rules. Started with (--no-update) flag.")

    traefik = TraefikClient(args['--traefik-addr'])
    routes_actor = RouteManager(traefik)

    mdk_runtime = defaultRuntime()
    mdk_runtime.dependencies.registerService("failurepolicy_factory", CircuitBreakerFactory())

    client = mdk_discovery.protocol.createClient(routes_actor, os.environ["DATAWIRE_TOKEN"], mdk_runtime)
    mdk_runtime.dispatcher.startActor(client)


def run_listener(args):
    logger.info("Starting API Gateway Listener")
    if args['listen']:
        listen(args)

    return


def main():
    exit(run_listener(docopt(__doc__, version="listener.py {0}".format('?'))))


if __name__ == "__main__":
    main()
