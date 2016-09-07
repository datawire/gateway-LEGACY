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
from mdk_runtime import defaultRuntime
from traefik import TraefikClient

from gateway import log_format
import logging
import mdk_discovery
import os
import semantic_version
import sys

from pythonjsonlogger import jsonlogger

logger = logging.getLogger('listener')
logger.setLevel(logging.DEBUG)
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
        if message.__class__ not in {NodeActive, NodeExpired}:
            pass

        message.node = RouteManager.__normalize_node(message.node)
        if isinstance(message, NodeActive) and RouteManager.__is_public(message.node):
            self.upsert_backend(message)
            self.upsert_frontend(message)
        elif isinstance(message, NodeExpired):
            self.remove_frontend(message)
            self.remove_backend(message)

        self.__reconfigure()

    def __reconfigure(self):
        routes = {
            'frontends': self.frontends,
            'backends': self.backends
        }

        if self._update:
            logger.debug("Reconfiguring Traefik",
                         extra={'frontends_count': len(self.frontends), 'backends_count': len(self.backends)})

            self._traefik.reconfigure(routes)

    @staticmethod
    def __normalize_node(node):
        # A little bit of defensive coding to avoid people who assign null where there should not be a null.
        if node.properties is None:
            node.properties = {}

        return node

    @staticmethod
    def __is_public(node):
        # This needs to become False in the future I think...
        return bool(node.properties.get('MDK_GATEWAY_PUBLIC_SERVICE', True))

    @staticmethod
    def __create_frontend_id(service, version):
        return "fe-{}-v{}".format(service, version)

    @staticmethod
    def __create_backend_id(service, version):
        return "be-{}-v{}".format(service, version)

    def upsert_backend(self, active):
        node = active.node
        props = node.properties if node.properties is not None else {}

        if semantic_version.validate(node.version):
            self.__upsert_semver_backend(node, props, semantic_version.Version(node.version))
        else:
            self.__upsert_backend(node, props, node.version)

    def __upsert_backend(self, node, props, version):
        be_id = 'be-{}-v{}'.format(node.service, version)

        if be_id not in self.backends:
            logger.info("Adding new backend (id: %s)", be_id)
            self.backends[be_id] = {
                'LoadBalancer': {
                    'method': 'drr'
                },
                'servers': {}
            }
        else:
            logger.debug("Backend already present (id: %s)", be_id)

        node_id = props['datawire_nodeId']

        be_servers = self.backends[be_id]['servers']
        be_servers[node_id] = {'url': node.address}

    def __upsert_semver_backend(self, node, props, semver):
        # pre-release software is special in semver and doesn't belong in the general population.
        if not semver.prerelease:
            for version in [str(semver.major), "{}.{}".format(semver.major, semver.minor)]:
                self.__upsert_backend(node, props, version)

        self.__upsert_backend(node, props, str(semver))

    def __upsert_frontend(self, node, props, version):
        fe_id = RouteManager.__create_frontend_id(node.service, version)
        be_id = RouteManager.__create_backend_id(node.service, version)

        if fe_id not in self.frontends:
            logger.info("Adding new frontend (id: %s)", fe_id)
            self.frontends[fe_id] = {'backend': be_id, 'routes': {}}
        else:
            logger.debug("Frontend already present (id: %s)", be_id)

        fe = self.frontends[fe_id]
        fe_routes = fe['routes']

        if 'api' not in fe_routes:
            fe_routes['api'] = {}

        path_prefix_format = props.get('MDK_GATEWAY_PATH_PREFIX', '/%(SERVICE_NAME)s/api/v%(SERVICE_VERSION)s')
        path_prefix = path_prefix_format.strip() % {
            'SERVICE_NAME': node.service,
            'SERVICE_VERSION': version
        }

        if not path_prefix.startswith("/"):
            path_prefix = '/' + path_prefix

        fe_routes['api'] = {
            'rule': 'PathPrefixStrip: {}'.format(path_prefix)
        }

    def __upsert_semver_frontend(self, node, props, semver):
        # pre-release software is special in semver and doesn't belong in the general population.
        if not semver.prerelease:
            for version in [str(semver.major), "{}.{}".format(semver.major, semver.minor)]:
                self.__upsert_frontend(node, props, version)

        self.__upsert_frontend(node, props, str(semver))

    def upsert_frontend(self, active):
        node = active.node
        props = node.properties if node.properties is not None else {}

        if semantic_version.validate(node.version):
            self.__upsert_semver_frontend(node, props, semantic_version.Version(node.version))
        else:
            self.__upsert_frontend(node, props, node.version)

    def remove_frontend(self, expire):
        node = expire.node
        props = node.properties if node.properties is not None else {}

        if semantic_version.validate(node.version):
            self.__remove_semver_frontend(node, props, semantic_version.Version(node.version))
        else:
            self.__remove_frontend(node, props, node.version)

    def __remove_semver_frontend(self, node, props, semver):
        for version in [str(semver.major), "{}.{}".format(semver.major, semver.minor), str(semver)]:
            self.__remove_frontend(node, props, version)

    def __remove_frontend(self, node, props, version):
        fe_id = RouteManager.__create_frontend_id(node.service, version)
        be_id = RouteManager.__create_backend_id(node.service, version)

        if fe_id in self.frontends and len(self.backends.get(be_id, [])) == 0:
            logger.info("Removing frontend because there are no more backends (id: %s)", fe_id)
            del self.frontends[fe_id]

    def remove_backend(self, expire):
        node = expire.node
        props = node.properties if node.properties is not None else {}

        if semantic_version.validate(node.version):
            self.__remove_semver_backend(node, props, semantic_version.Version(node.version))
        else:
            self.__remove_backend(node, props, node.version)

    def __remove_semver_backend(self, node, props, semver):
        if not semver.prerelease:
            for version in [str(semver.major), "{}.{}".format(semver.major, semver.minor)]:
                self.__remove_backend(node, props, version)

        self.__remove_backend(node, props, semver)

    def __remove_backend(self, node, props, version):
        be_id = "be-{}-v{}".format(node.service, version)

        import pprint

        print("Removing backend {}".format(node.service))
        pprint.pprint(props)

        if be_id in self.backends:
            logger.info("Removing backend (id: %s)", be_id)
            node_id = props['datawire_nodeId']
            be_servers = self.backends[be_id]['servers']

            if node_id in be_servers:
                del be_servers[node_id]
                logger.debug("Removed node from backend (node: %s, backend: %s)", node_id, be_id)
                if len(be_servers) == 0:
                    del self.backends[be_id]
                    logger.debug("Removed unused backend (backend: %s)", be_id)
            else:
                logger.debug("Could not remove unknown node (id: %s)", node_id)


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
    mdk_runtime.dependencies.registerService("failurepolicy_factory", CircuitBreakerFactory(mdk_runtime))

    client = mdk_discovery.protocol.DiscoClientFactory(os.environ["DATAWIRE_TOKEN"]).create(routes_actor, mdk_runtime)
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
