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

import requests
import json


class TraefikClient(object):

    """Interact with the Traefik HTTP API. Currently only supports full updates of the entire routing rules.

    Arguments:
        traefik_address -- The address of the Traefik server to communicate with in <host>[:<port] format.

    Keyword arguments:
        use_https -- Indicate whether the API client should use HTTP or HTTPS.
    """

    def __init__(self, traefik_address, use_https=False):
        if traefik_address is None:
            raise ValueError("traefik_address must be in the format <host>[:port].")

        scheme = "https:" if bool(use_https) else "http:"
        self.base_url = "{}//{}/api/providers/web".format(scheme, traefik_address)

    def reconfigure(self, routes):

        """Reconfigures the entire routing configuration for the server."""

        data = json.dumps(routes)
        requests.put(self.base_url, data)
