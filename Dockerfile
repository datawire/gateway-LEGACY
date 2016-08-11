FROM alpine:3.4
MAINTAINER Datawire <dev@datawire.io>
LABEL PROJECT_REPO_URL = "git@github.com:datawire/gateway.git" \
      PROJECT_REPO_BROWSER_URL = "https://github.com/datawire/gateway" \
      DESCRIPTION = "Datawire Gateway" \
      VENDOR = "Datawire" \
      VENDOR_URL = "https://datawire.io/"

ENV SUPERVISOR_VERSION="3.3.0" TRAEFIK_VERSION="1.0.2"

WORKDIR /opt/datawire/fluxcapacitor/gateway
COPY gateway/ ./

WORKDIR /opt/datawire/fluxcapacitor
COPY requirements.txt requirements-quark.txt entrypoint.sh traefik.toml ./

RUN apk --no-cache add \
    bash \
    ca-certificates \
    curl \
    ncurses \
    python \
    py-pip \
    py-virtualenv \
    wget \
  && ln -snf /bin/bash /bin/sh \
  && wget https://github.com/containous/traefik/releases/download/v${TRAEFIK_VERSION}/traefik \
  && chmod +x traefik \
  && pip install -U  pip \
  && pip install -Ur requirements.txt supervisor==${SUPERVISOR_VERSION} \
  && rm requirements.txt

# Install Datawire MDK (used by Datawire Gateway)
ADD https://raw.githubusercontent.com/datawire/quark/master/install.sh .
ENV PATH $HOME/.quark/bin:$PATH
RUN bash install.sh

RUN ${HOME}/.quark/bin/quark install \
    --python $(sed -e '/^[[:space:]]*$$/d' -e '/^[[:space:]]*\#/d' requirements-quark.txt | tr '\n' ' ' )

EXPOSE 8080 8000
ENTRYPOINT ["./entrypoint.sh"]
