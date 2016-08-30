# Makefile: fluxcapacitor

SERVICE_NAME=$(shell cat Datawirefile | python -c 'import sys, json; print json.load(sys.stdin)["service"]["name"]')
SERVICE_VERSION=$(shell cat Datawirefile | python -c 'import sys, json; print json.load(sys.stdin)["service"]["version"]')

QUARK_REQUIREMENTS=$(shell sed -e '/^[[:space:]]*$$/d' -e '/^[[:space:]]*\#/d' requirements-quark.txt | tr '\n' ' ' )

DOCKER_REPO=datawire/fluxcapacitor

.PHONY: all

all: clean build

build:
	# Produces a language build artifact (e.g.: .jar, .whl, .gem). Alternatively a GZIP tarball
	# can be provided if more appropriate.
	:
 
docker:
	# Produces a Docker image.
	docker build -t $(DOCKER_REPO):$(SERVICE_VERSION) -t $(DOCKER_REPO):latest .

docker-bash:
	docker run -i -t --entrypoint /bin/bash datawire/fluxcapacitor:$(SERVICE_VERSION)
 
clean:
	# Clean previous build outputs (e.g. class files) and temporary files. Customize as needed.
	:
 
compile:
	# Compile code (may do nothing for interpreted languages).
	:

quark-requirements:
	# Compiles AND installs Quark language sources if there are any.
	~/.quark/bin/quark install --python $(QUARK_REQUIREMENTS)

quark-requirements-venv: venv
	# Compiles AND installs Quark language sources if there are any.
	( \
		. venv/bin/activate; \
		~/.quark/bin/quark install --python $(QUARK_REQUIREMENTS); \
	)

publish: docker
	docker push datawire/fluxcapacitor

publish-no-build:
	docker push datawire/fluxcapacitor
	
run-dev: venv
	# Run the service or application in development mode.
	venv/bin/python service/service.py

run-docker: docker run-docker-no-rebuild
	:

run-docker-no-rebuild:
	# Run the service or application in production mode.
	docker run --rm --net="host" --name datawire-fluxcapacitor -e DATAWIRE_TOKEN=$(DATAWIRE_TOKEN) -it -p 8000:8000 -p 8080:8080 $(DOCKER_REPO):$(SERVICE_VERSION)
	
test: venv
	# Run the full test suite.

unit-test: venv
	# Run only the unit tests.

version:
	@echo VERSION

# Python virtualenv automatic setup. Ensures that targets relying on the virtualenv always have an updated python to
# use.
#
# This is intended for developer convenience. Do not attempt to make venv in a Docker container or use a virtualenv in
# docker container because you will be going down into a world of darkness.

venv: venv/bin/activate

venv/bin/activate: requirements.txt
	test -d venv || virtualenv venv
	venv/bin/pip install -Ur requirements.txt
	touch venv/bin/activate
