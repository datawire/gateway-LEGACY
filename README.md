# Datawire Flux Capacitor

Intelligent and fast API gateway for the Datawire Microservices Platform built atop of the excellent [Traefik](https://github.com/containous/traefik) HTTP reverse proxy. 

## Getting Started

Super simple!

```bash
export DATAWIRE_TOKEN="<Your Access Token>"
docker pull datawire/fluxcapacitor:latest
docker run --rm -it --net="host" -p 8080:8080 -p 8000:8000 -e DATAWIRE_TOKEN=$DATAWIRE_TOKEN datawire/fluxcapacitor
```

## How to Use

1. Register a service with the Datawire Discovery service.
2. The service name becomes the root of the URL path. For example, if your service is named 'time' then you would access the service via the URL of http://127.0.0.1:8080/time (this will eventually be configurable).

## Gotchas

Known issues and features that are a WIP. 

1. Flux Capacitor does not support service versions (e.g mapping 1.0.1 to a URL such as /v1).
2. HTTPS is not (yet) supported. The v1.0 expected deployment pattern is to put a Layer 7 cloud balancer (e.g. AWS Elastic Load Balancer, Google Cloud Load Balancer etc.) in front of Flux Capacitor instances and use those to perform TLS offloading.
3. The generated URL's are not configurable but this will eventually be supported.

## License

Datawire Gateway is open-source software licensed under **Apache 2.0**. Please see [LICENSE](LICENSE) for further details.
