# Makefile — audiolayers
# Usa il Python del venv se presente, altrimenti quello di sistema.

ifeq ($(OS),Windows_NT)
    PYTHON := $(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python)
else
    # In WSL il venv Windows è utilizzabile via interop (.exe): un solo venv
    # per entrambi i mondi. Un eventuale venv Linux nativo ha la precedenza.
    PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,$(if $(wildcard .venv/Scripts/python.exe),.venv/Scripts/python.exe,python3))
endif

# Partitura da renderizzare: make render SCORE=path/to/score.yaml
SCORE ?=

.PHONY: tests test unit integration golden e2e install render setup

tests: ## Suite completa
	$(PYTHON) -m pytest

test: tests

unit: ## Solo unit test
	$(PYTHON) -m pytest tests/unit

integration: ## Solo integration test
	$(PYTHON) -m pytest tests/integration

golden: ## Solo golden test
	$(PYTHON) -m pytest tests/golden -m golden

e2e: ## Solo end-to-end
	$(PYTHON) -m pytest tests/e2e -m e2e

install: ## Installa/aggiorna dipendenze nel venv
	$(PYTHON) -m pip install -r requirements.txt

render: ## Renderizza una partitura: make render SCORE=path/to/score.yaml
	$(PYTHON) -m audiolayers.main $(SCORE)

setup: ## Configura direnv + tab-completion zsh (da WSL/zsh)
	@zsh setup.sh
