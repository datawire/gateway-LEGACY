#!/usr/bin/env bash

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

if [ -f /etc/minimal-resolv.conf ]; then
    if [ -f /etc/resolv.conf ]; then
        cp /etc/resolv.conf /etc/dnsmasq-resolv.conf
    else
        echo "nameserver 10.0.0.10" > /etc/dnsmasq-resolv.conf
    fi

    cat /etc/minimal-resolv.conf > /etc/resolv.conf
    rm /etc/minimal-resolv.conf
fi

dnsmasq --local-service

(python -m gateway.listener listen &) && ./traefik -c traefik.toml -d