FROM alpine:3.4
MAINTAINER Datawire <dev@datawire.io>
LABEL PROJECT_REPO_URL = "git@github.com:datawire/gateway.git" \
      PROJECT_REPO_BROWSER_URL = "https://github.com/datawire/gateway" \
      DESCRIPTION = "Datawire Gateway" \
      VENDOR = "Datawire" \
      VENDOR_URL = "https://datawire.io/"

ENV TRAEFIK_VERSION "1.0.2"

RUN apk --no-cache add \
    bash \
    curl \
    ncurses \
    python \
    py-pip \
    py-virtualenv \
  && ln -snf /bin/bash /bin/sh \
  && pip install --upgrade pip

WORKDIR /opt
COPY . /opt

# Install Traefik
ADD https://github.com/containous/traefik/releases/download/v1.0.2/traefik .

# Install Datawire MDK (used by Datawire Gateway)
ADD https://raw.githubusercontent.com/datawire/quark/master/install.sh .
ENV PATH $HOME/.quark/bin:$PATH
RUN bash install.sh

RUN  pip install -Ur requirements.txt \
     && ${HOME}/.quark/bin/quark install \
        --python $(sed -e '/^[[:space:]]*$$/d' -e '/^[[:space:]]*\#/d' requirements-quark.txt | tr '\n' ' ' )

EXPOSE 32990
ENTRYPOINT ["./entrypoint.sh"]
