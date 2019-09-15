.PHONY: plugins

GOFLAGS="-mod=vendor"
GOPATH0 := $(firstword $(subst :, ,$(GOPATH)))
UTIL_PATH := github.com/alpacahq/marketstore/utils


debug:
	$(MAKE) debug -C contrib/ondiskagg
	$(MAKE) debug -C contrib/gdaxfeeder
	$(MAKE) debug -C contrib/slait
	$(MAKE) debug -C contrib/stream
	$(MAKE) debug -C contrib/polygon
	$(MAKE) debug -C contrib/bitmexfeeder
	$(MAKE) debug -C contrib/binancefeeder
	$(MAKE) debug -C contrib/iex
	$(MAKE) debug -C contrib/xignitefeeder
	GOFLAGS=$(GOFLAGS) go install -gcflags="all=-N -l" -ldflags "-X $(UTIL_PATH).Tag=$(DOCKER_TAG) -X $(UTIL_PATH).BuildStamp=$(shell date -u +%Y-%m-%d-%H-%M-%S) -X $(UTIL_PATH).GitHash=$(shell git rev-parse HEAD)" ./...

install:
	GOFLAGS=$(GOFLAGS) go install -ldflags "-s -X $(UTIL_PATH).Tag=$(DOCKER_TAG) -X $(UTIL_PATH).BuildStamp=$(shell date -u +%Y-%m-%d-%H-%M-%S) -X $(UTIL_PATH).GitHash=$(shell git rev-parse HEAD)" ./...

generate:
	make -C sqlparser
	GOFLAGS=$(GOFLAGS) go generate $(shell find . -path ./vendor -prune -o -name \*.go -exec grep -q go:generate {} \; -print | while read file; do echo `dirname $$file`; done | xargs)

vendor:
	GOFLAGS=$(GOFLAGS) go mod vendor

update:
	GOFLAGS=$(GOFLAGS) go mod tidy

plugins:
	$(MAKE) -C contrib/ondiskagg
	$(MAKE) -C contrib/gdaxfeeder
	$(MAKE) -C contrib/slait
	$(MAKE) -C contrib/stream
	$(MAKE) -C contrib/polygon
	$(MAKE) -C contrib/bitmexfeeder
	$(MAKE) -C contrib/binancefeeder
	$(MAKE) -C contrib/iex
	$(MAKE) -C contrib/xignitefeeder

test:
	GOFLAGS=$(GOFLAGS) go fmt ./...
	$(MAKE) unittest
	$(MAKE) integration-test

integration-test: install
	$(MAKE) -C tests/integ test

unittest:
	GOFLAGS=$(GOFLAGS) go test ./...

image:
	docker build . -t marketstore:latest -f $(DOCKER_FILE_PATH)

push:
	docker build --build-arg tag=$(DOCKER_TAG) -t alpacamarkets/marketstore:$(DOCKER_TAG) -t alpacamarkets/marketstore:latest .
	docker login -u $(DOCKER_USER) -p $(DOCKER_PASS)
	docker push alpacamarkets/marketstore:$(DOCKER_TAG)
	docker push alpacamarkets/marketstore:latest

