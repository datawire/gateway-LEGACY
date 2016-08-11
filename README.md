# Datawire Flux Capacitor

Intelligent and fast API gateway for the Datawire Microservices Platform built atop of the excellent [Traefik](https://github.com/containous/traefik) HTTP reverse proxy. 

# Getting Started

Super simple!

```bash
export DATAWIRE_TOKEN="<Your Access Token>"
docker pull datawire/fluxcapacitor:latest
docker run --rm -it --net="host" -p 8080:8080 -p 8000:8000 -e DATAWIRE_TOKEN=$DATAWIRE_TOKEN datawire/fluxcapacitor
```

# License

Datawire Gateway is open-source software licensed under **Apache 2.0**. Please see [LICENSE](LICENSE) for further details.
