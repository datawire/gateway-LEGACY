FROM alpine:3.4
MAINTAINER Datawire <dev@datawire.io>
LABEL PROJECT_REPO_URL = "git@github.com:datawire/gateway.git" \
      PROJECT_REPO_BROWSER_URL = "https://github.com/datawire/gateway" \
      DESCRIPTION = "Datawire Gateway" \
      VENDOR = "Datawire" \
      VENDOR_URL = "https://datawire.io/"

ENV TRAEFIK_VERSION="1.0.2"

WORKDIR /opt/fluxcapacitor
COPY requirements.txt \
     entrypoint.sh \
     traefik.toml \
     ./

COPY gateway/ ./gateway

RUN apk --no-cache add \
    bash \
    ca-certificates \
    python \
    py-pip \
    wget \
  && ln -snf /bin/bash /bin/sh \
  && wget https://github.com/containous/traefik/releases/download/v${TRAEFIK_VERSION}/traefik \
  && chmod +x traefik \
  && pip install -U  pip \
  && pip install -Ur requirements.txt \
  && rm requirements.txt

EXPOSE 8080 8000
ENTRYPOINT ["./entrypoint.sh"]
