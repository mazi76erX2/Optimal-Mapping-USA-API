SHELL = /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
.DEFAULT_GOAL := help

include .env
export $(shell sed 's/=.*//' .env)
export PYTHONPATH
export PIPENV_VENV_IN_PROJECT=1

PYTHON := python3
PIP := $(PYTHON) -m pip
PIPENV := $(PYTHON) -m pipenv

POSTGRES_COMMAND := /Applications/Postgres.app/Contents/Versions/latest/bin

APP_NAME = server:0.0.1
APP_DIR = server
TEST_SRC = $(APP_DIR)/tests

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

### Local commands ###

venv:
	$(PIP) install -U pipenv
	$(PIPENV) shell

install-packages:
	pipenv install --dev
