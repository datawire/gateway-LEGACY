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

"""hello.py

Acts as a very basic web service for testing various Gateway features

Usage:
    hello.py serve [options]
    hello.py (-h | --help)
    hello.py --version

Options:
    --srv-version=<version> Set the version published by the service.
    --srv-name=<name>       Set the name published by the service.
    --public                Set the service as public.
    --bind=<addr>           Set the bind address [default: 127.0.0.1]
    --port=<port>           Set the listen port [default: 5000]
    -h --help               Show the help.
    --version               Show the version.
"""

import atexit
import json
import mdk
import mdk_discovery
import os

from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler

from docopt import docopt

service_name = None
service_version = None


class HelloHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        content_type = 'application/json; charset=utf-8'

        if self.path == "/hello" or self.path == "":
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.wfile.write('\n')
            json.dump(
                {'msg': 'Hello, world!', 'version': service_version}, self.wfile)
        elif self.path == "/health":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.wfile.write('\n')
            json.dump({'version': self.version}, self.wfile)
        else:
            self.send_response(404)


def run_hello(args):
    m = mdk.init()

    global service_name
    service_name = args['--srv-name']

    global service_version
    service_version = args['--srv-version']
    public = '--public' in args

    addr = os.getenv('DATAWIRE_ROUTABLE_HOST', args['--bind'])
    port = int(os.getenv('DATAWIRE_ROUTABLE_PORT', args['--port']))

    node = mdk_discovery.Node()
    node.service = service_name
    node.version = service_version

    node.address = "http://{}:{}".format(addr, port)
    node.properties = {'datawire_nodeId': m.procUUID, 'MDK_GATEWAY_PUBLIC_SERVICE': public}

    m._disco.register(node)
    m.start()

    atexit.register(m.stop)

    server = HTTPServer((addr, port), HelloHandler)
    server.serve_forever()


def main(args):
    exit(run_hello(docopt(__doc__, argv=args[1:], version="hello ?")))


if __name__ == "__main__":
    import sys
    main(sys.argv)
