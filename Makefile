# waku-agent — one command per pillar.
#
# Make is not a framework — it's a 45-year-old command shortcut tool that
# ships with every Mac/Linux. Each target below is just the shell command
# you'd otherwise type. `make run` = "run the python below", nothing more.
#
# Let uv pick/create the project environment on every platform. The old
# POSIX-only `[ -x .venv/bin/python ]` probe breaks under PowerShell/cmd.
export UV_CACHE_DIR ?= $(CURDIR)/.uv-cache
export UV_PYTHON_INSTALL_DIR ?= $(CURDIR)/.uv-python
export UV_PROJECT_ENVIRONMENT ?= $(CURDIR)/.uv-make-venv
export TMP ?= $(CURDIR)/.tmp
export TEMP ?= $(CURDIR)/.tmp
export TMPDIR ?= $(CURDIR)/.tmp
export PYTEST_ADDOPTS ?= -p no:cacheprovider --basetemp=$(CURDIR)/.tmp/pytest
export GIT_CONFIG_COUNT ?= 1
export GIT_CONFIG_KEY_0 ?= safe.directory
export GIT_CONFIG_VALUE_0 ?= $(CURDIR)
UV := $(CURDIR)/.codex-tools/uv/bin/uv.exe
PY := $(UV) run python
PY_EVAL := $(UV) run --extra eval python

.PHONY: run voice telegram discord brief dashboard trace eval eval-judge gate lint
.PHONY: run voice telegram whatsapp brief dashboard trace eval eval-judge gate lint

.tmp:
	powershell -NoProfile -Command "New-Item -ItemType Directory -Force -Path '.tmp' | Out-Null"

run:            ## chat with Waku in the terminal
	$(PY) -m waku

voice:          ## talk to it — push-to-talk, or always-on with WAKU_WAKE_WORD
	$(PY) -m waku voice

telegram:       ## phone → laptop (needs TELEGRAM_BOT_TOKEN in .env)
	$(PY) -m waku telegram

discord:        ## Discord → laptop (needs DISCORD_BOT_TOKEN in .env)
	$(PY) -m waku discord
whatsapp:       ## WhatsApp → laptop (needs WHATSAPP_TOKEN in .env, public URL)
	$(PY) -m waku whatsapp

brief:          ## morning briefing from calendar + mail + memory (as a LOOP)
	$(PY) -m waku brief

gather:         ## same job as a GRAPH: 4 sources in parallel, then one digest
	$(PY) -m waku gather

# The server holds dashboard.py in memory: static JS/CSS reload on refresh, but
# Python routes do NOT. After pulling a change that touches dashboard.py (or any
# imported module), stop this and re-run it, or the UI shows stale backend data.
dashboard:      ## everything on one page — http://localhost:7777 (restart after a backend pull)
	$(PY) -m waku.ops.dashboard

trace:          ## deep trace waterfalls (Phoenix) at http://localhost:6006
	$(PY) -m phoenix.server.main serve

eval: .tmp      ## deterministic evals (0/1, no judge involved)
	$(PY_EVAL) -m pytest -q evals/deterministic

eval-judge: .tmp ## LLM-as-judge evals (scored %, needs an API key)
	$(PY_EVAL) -m pytest -q evals/judge

gate: .tmp      ## the release gate: deterministic must pass, judge must clear threshold
	$(PY_EVAL) -m waku.ops.release_gate

shootout:       ## same tasks, different brains: make shootout RUNS="kimi:kimi-k3 anthropic:claude-opus-4-8"
	$(PY) scripts/shootout.py $(RUNS)

shootout-coding: ## coding round via pi, scored by tests: make shootout-coding RUNS="kimi:kimi-k3 anthropic:claude-opus-4-8"
	$(PY) scripts/shootout.py $(RUNS) --coding

lint:
	$(PY) -m ruff check waku evals scripts
