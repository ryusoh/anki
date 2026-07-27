.PHONY: help fetch fetch-r2 verify-r2 check precommit precommit-fix fmt fmt-check sync-check lint lint-js lint-css lint-fix depcheck typecheck-js hooks \
	quality-py lint-py fmt-py fmt-py-check typecheck security-py install-dev coverage-rank verify mutate-py mutate-js \
	complexity-py imports-py

PYTHON := $(if $(wildcard .venv/bin/python3),"$(CURDIR)/.venv/bin/python3",python3)
NPM := npm

# Core count for the parallel verify gate (see `verify` target below). sysctl
# is macOS; nproc covers Linux CI runners; 4 is a safe last-resort default.
JOBS ?= $(shell sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)

# Fail loudly if an installed dev tool has drifted from its requirements-dev.txt
# pin, instead of silently formatting/linting with the wrong version — a stale
# .venv can pass this locally and still turn CI red (or vice versa). Usage:
# $(call CHECK_TOOL_VERSION,black)
define CHECK_TOOL_VERSION
pinned=$$(grep -m1 '^$(1)==' requirements-dev.txt | cut -d= -f3); \
installed=$$($(PYTHON) -m $(1) --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1); \
if [ -n "$$pinned" ] && [ "$$pinned" != "$$installed" ]; then \
	echo "⊘ $(1) $$installed installed but requirements-dev.txt pins $$pinned — .venv is stale."; \
	echo "  This can pass locally and still fail in CI (or vice versa). Fix: make install-dev"; \
	exit 1; \
fi
endef

# File patterns for formatters/linters (exclude vendor, data, and node_modules directories)
JS_FILES := $(shell git ls-files --cached --others --exclude-standard '*.js' 2>/dev/null | grep -v '^js/vendor/' | grep -v '^assets/vendor/' | grep -v '^data/' | grep -v '^coverage/' | grep -v 'node_modules' | grep -v '\.min\.js$$' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
CSS_FILES := $(shell git ls-files --cached --others --exclude-standard '*.css' 2>/dev/null | grep -v '^assets/vendor/' | grep -v '^coverage/' | grep -v '\.min\.css$$' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
MD_FILES := $(shell git ls-files --cached --others --exclude-standard '*.md' 2>/dev/null | grep -v '^coverage/' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
HTML_FILES := $(shell git ls-files --cached --others --exclude-standard '*.html' 2>/dev/null | grep -v '^coverage/' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
JSON_FILES := $(shell git ls-files --cached --others --exclude-standard '*.json' 2>/dev/null | grep -v '^data/' | grep -v '^graph/' | grep -v '^coverage/' | grep -v 'package-lock.json' | grep -v 'custom_stats_data.json' | grep -v 'review_stats_data.json' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
PRETTIER_FILES := $(JS_FILES) $(CSS_FILES) $(MD_FILES) $(HTML_FILES) $(JSON_FILES)

# Python we own and maintain — now spans the addons that were originally
# installed from AnkiWeb but which we modify in this repo. The only Python kept
# out of the gates is genuinely vendored code (e.g. review_heatmap/libaddon and
# its _vendor/ packages), excluded via the tool configs (pyproject.toml /
# mypy.ini / .bandit), not here.
PY_SRC := auto_image auto_mathjax auto_wiktionary data/anki graph \
	highlight_search_matches prioritize_front_field_search remove_deck_highlight \
	rewrite_text_of_study_cards stats_page_customizer strip_html_tags \
	unify_review_count_colors tabbed_stats tools \
	awesome_tts review_heatmap enhance_main_window custom_background \
	animated_glass_background mac_transparent_titlebar hide_window_title \
	hide_deck_collapse toggle_bottom_pane
PY_ALL := $(PY_SRC) tests conftest.py

help:
	@echo "Targets:"
	@echo "  install        Install Python dependencies"
	@echo "  fetch          Fetch Anki stats to Git-friendly format"
	@echo "  fetch-r2       Upload private Anki content to Cloudflare R2"
	@echo "  verify-r2      Audit hash map vs live R2 bucket (read-only)"
	@echo "  graph-analyze  Analyze all decks with PageRank"
	@echo "  graph-deck     Analyze specific deck (DECK='name')"
	@echo "  graph-export   Export graphs to graph_output/"
	@echo "  pagerank       PageRank report for latest reviewed day"
	@echo "  pagerank-all   PageRank reports for all reviewed days"
	@echo "  check          Run all tests"
	@echo "  test-py        Fast scoped Python test (SUITE=auto_wiktionary/tests)"
	@echo "  precommit      Run all pre-commit checks (no fixes)"
	@echo "  precommit-fix  Auto-fix issues and run pre-commit checks"
	@echo "                 YOLO=1 to auto-yes all prompts (background mode)"
	@echo "                 MSG='msg' to commit and push after checks pass"
	@echo "  fmt            Format code (Prettier)"
	@echo "  fmt-check      Check formatting (dry-run)"
	@echo "  lint           Run JS+CSS+Markdown linters (ESLint/Stylelint/markdownlint) + depcheck"
	@echo "  depcheck       JS dependency-structure gate (dependency-cruiser, no cycles)"
	@echo "  lint-fix       Auto-fix JS/CSS/Markdown lint issues"
	@echo "  typecheck-js   JS strict type check (tsc --checkJs on whitelist)"
	@echo "  quality-py     Python lint/format/type/security/complexity/imports (ruff/black/mypy/bandit/xenon/import-linter)"
	@echo "  mutate-py      Mutation smoke run (mutmut on strip_html_tags; NOT part of any gate)"
	@echo "  fmt-py         Auto-format Python (black + ruff --fix)"
	@echo "  hooks          Install git pre-commit hook"

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

# Bootstrap .venv when missing. In a linked git worktree, symlink the main
# checkout's .venv (instant, and shares the pinned tools); otherwise create a
# fresh one. Without this, a fresh worktree's install targets fell back to the
# system python3 (whose ancient pip can't even resolve the pinned tools).
# Note: $(PYTHON) resolves at Makefile parse time — before this target has
# run — so the install recipes below invoke .venv/bin/python3 directly.
.venv:
	@common_dir=$$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null); \
	main_root=$$(dirname "$$common_dir"); \
	if [ -n "$$common_dir" ] && [ "$$main_root" != "$(CURDIR)" ] && [ -d "$$main_root/.venv" ]; then \
		echo "🔗 Linking .venv from main checkout ($$main_root/.venv)..."; \
		ln -s "$$main_root/.venv" .venv; \
	else \
		echo "🐍 Creating .venv..."; \
		python3 -m venv .venv; \
	fi

# Stamped so `precommit-fix` (via these targets, not `install`) skips npm
# ci/pip install entirely when the lockfile/requirements haven't changed —
# npm ci alone is ~15s on every invocation otherwise. `.make/` is gitignored.
# FORCE_INSTALL=1 makes both unconditional (mirrors plain `install` below).
ifeq ($(FORCE_INSTALL),1)
.PHONY: .make/npm-ci.stamp .make/pip.stamp
endif

.make/npm-ci.stamp: package-lock.json | .venv
	@echo "📦 Syncing JS dependencies (npm ci, respects package-lock.json exactly)..."
	@npm ci
	@mkdir -p .make
	@touch $@

.make/pip.stamp: requirements.txt | .venv
	@echo "📦 Installing Python dependencies..."
	@.venv/bin/python3 -m pip install -q -r requirements.txt
	@mkdir -p .make
	@touch $@

# Explicit `make install` always (re)installs regardless of the stamps —
# precommit-fix depends on the stamped targets above instead of this one.
install: | .venv
	@rm -f .make/pip.stamp .make/npm-ci.stamp
	@$(MAKE) .make/pip.stamp .make/npm-ci.stamp
	@echo "✅ Dependencies installed"

install-dev: | .venv
	@echo "📦 Installing Python dev/lint dependencies..."
	@.venv/bin/python3 -m pip install -q -r requirements-dev.txt
	@echo "✅ Dev dependencies installed"

# -----------------------------------------------------------------------------
# Data Fetching
# -----------------------------------------------------------------------------

fetch:
	@python3 data/anki/fetch

fetch-and-stage-r2:
	@echo "📦 Fetching Anki data (GitHub + R2 staging)..."
	@python3 data/anki/fetch --stage-r2 --verbose
	@echo "✅ GitHub data exported + R2 files staged"

fetch-r2-skip-fetch:
	@echo "📤 Uploading already-staged R2 files (with sync)..."
	@python3 data/anki/upload-to-r2 --upload-only --sync --verbose

fetch-r2:
	@echo "📤 Uploading private Anki content to Cloudflare R2..."
	@python3 data/anki/upload-to-r2 --sync --verbose

verify-r2:
	@echo "🔎 Auditing hash map against live R2 bucket (read-only)..."
	@$(PYTHON) data/anki/verify-hash-map.py

# -----------------------------------------------------------------------------
# Graph Analysis
# -----------------------------------------------------------------------------

graph-analyze:
	@python3 graph/analyze.py --all-decks --top 10 --compare

graph-deck:
	@if [ -z "$(DECK)" ]; then \
		echo "Usage: make graph-deck DECK='Deck Name'"; \
		echo ""; \
		echo "Deck aliases:"; \
		echo "  J, 1  - 言語日語 (Japanese)"; \
		echo "  C, 2  - 言語粵語 (Cantonese)"; \
		echo "  E, 3  - 言語英語 (English)"; \
		echo "  S, 4  - 言語呉語 (Wu/Shanghai)"; \
		echo "  T, 5  - 言語台語 (Taiwanese)"; \
		echo "  F, 6  - 金融 (Finance)"; \
	else \
		python3 graph/analyze.py --deck "$(DECK)" --top 10 --hubs --isolated; \
	fi

graph-export:
	@mkdir -p graph_output
	@python3 graph/analyze.py --all-decks --export graph_output --format json

graph-history:
	@python3 graph/export_history.py

graph-public:
	@echo "🌐 Exporting public anonymized graph data..."
	@python3 graph/export_data.py all --public
	@python3 graph/export_history.py --public
	@echo "✅ Public data created at graph/*_public.json"

graph-push: graph-public
	@python3 graph/upload_public.py


graph-local:
	@echo "📊 Exporting local private graph data..."
	@python3 graph/export_data.py all
	@python3 graph/export_history.py

graph-local-prompt:
	@echo ""
	@if [ "$(YOLO)" = "1" ]; then \
		echo "📊 Export local private Knowledge Graph data? auto-yes (YOLO)"; \
		$(MAKE) graph-local; \
	else \
		echo "📊 Export local private Knowledge Graph data? (y/n)"; \
		read -r response && \
		if [ "$$response" = "y" ] || [ "$$response" = "yes" ]; then \
			$(MAKE) graph-local; \
		fi; \
	fi

pagerank:
	@if [ -n "$(TOP)" ]; then \
		python3 graph/pagerank_report.py --top $(TOP); \
	else \
		python3 graph/pagerank_report.py; \
	fi

pagerank-all:
	@python3 graph/pagerank_report.py --all

graph-viz:
	@mkdir -p graph_output
	@python3 graph/export_viz.py --format html --output graph_output
	@echo ""
	@echo "✅ HTML visualizations created in graph_output/"
	@echo "📁 Open in browser:"
	@ls -1 graph_output/*.html 2>/dev/null | head -5

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

security:
	@echo ""
	@echo "🔒 EXTREMELY RIGOROUS SECURITY CHECK"
	@echo "   Scanning ALL tracked files for private Anki data..."
	@echo ""
	@python3 data/anki/security_check.py

audit:
	@echo ""
	@echo "🔍 FULL SECURITY AUDIT"
	@echo "   Scanning for credentials, private data, gitignore coverage..."
	@echo ""
	@python3 tools/security_audit.py

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

check: check-node check-py

# The jsdom-pin guard lives in a file, NOT as an inline `node -e ' \ ...'`
# script: macOS's bundled GNU make 3.81 collapses recipe backslash-newlines
# into one line (valid JS) but make 4.x on CI preserves them per POSIX — the
# shell keeps them literally inside single quotes and node dies with
# `SyntaxError: Expected unicode escape`. Same Makefile: green locally, red
# on CI (seen 2026-07-14). Never backslash-continue an interpreter script
# inside recipe quotes — pinned by
# tests/test_makefile_no_inline_multiline_scripts.py.
check-node:
	@node tools/check_jsdom_pin.mjs
	@COVDIR=$$(mktemp -d 2>/dev/null || mktemp -d -t c8cov); \
	NODE_V8_COVERAGE="$$COVDIR" node tools/node_test_runner.mjs; \
	STATUS=$$?; \
	rm -rf "$$COVDIR"; \
	if [ $$STATUS -eq 0 ]; then \
		NODE_OPTIONS="--experimental-vm-modules --no-warnings" npx jest --ci --colors review_heatmap/tests/; \
		STATUS=$$?; \
	fi; \
	exit $$STATUS

# Fast, scoped Python test for the tight edit→verify loop (no coverage).
# Always runs from the repo root (root conftest.py mocks aqt/anki).
#   make test-py SUITE=auto_wiktionary/tests
test-py:
	@if [ -z "$(SUITE)" ]; then \
		echo "Usage: make test-py SUITE=<dir>   e.g. SUITE=auto_wiktionary/tests"; \
	else \
		$(PYTHON) -m pytest -q "$(SUITE)"; \
	fi

test-addon:
	@if [ -z "$(ADDON)" ]; then \
		echo "Usage: make test-addon ADDON=<addon_dir>"; \
	else \
		$(PYTHON) -m pytest -q "$(ADDON)/tests"; \
	fi

typecheck-addon:
	@if [ -z "$(ADDON)" ]; then \
		echo "Usage: make typecheck-addon ADDON=<addon_dir>"; \
	else \
		mypy "$(ADDON)"; \
	fi

check-handler-regression:
	@node tests/handler_regression.test.mjs

check-handler-validation:
	@node tests/validateCommand.real.test.mjs

# Python test suites run as INDEPENDENT pytest invocations: each addon's tests
# bootstrap their own sys.path (e.g. `sys.path.insert(0, <addon>)`), so a single
# combined `pytest` run fails to collect. Coverage is accumulated across suites
# with --cov-append and reported once (mirrors check-node's JS coverage report).
# Requires pytest-cov (declared in requirements.txt) — run `make install` first.
#
# Auto-discovered (like JS_FILES/MD_FILES above): every directory holding a
# `test_*.py` becomes a suite, so a new addon's tests are gated the moment they
# are committed — no manual registration to forget. To intentionally opt a
# directory out, append it to PY_TEST_EXCLUDE with a reason.
PY_TEST_EXCLUDE :=
PY_TEST_SUITES := $(filter-out $(PY_TEST_EXCLUDE),$(shell git ls-files --cached --others --exclude-standard '*/test_*.py' 2>/dev/null | sed -E 's|/[^/]+$$||' | sort -u))

# Suites run as parallel sub-make jobs (one phony target per suite) instead of
# a serial loop: each gets its own COVERAGE_FILE (no shared state to race on)
# and coverage combine merges them after. -p no:cacheprovider avoids N pytest
# processes racing to write the same .pytest_cache/v/cache/* files — nothing
# here uses --lf/--ff so the cache plugin buys nothing anyway.
PY_COV_DIR := coverage/py-data
PY_SUITE_TARGETS := $(addprefix pysuite/,$(PY_TEST_SUITES))
.PHONY: $(PY_SUITE_TARGETS)
$(PY_SUITE_TARGETS): pysuite/%:
	@echo "  → $*"
	@COVERAGE_FILE="$(CURDIR)/$(PY_COV_DIR)/.coverage.$(subst /,_,$*)" \
		$(PYTHON) -m pytest -q -p no:cacheprovider --color=yes --cov --cov-report= "$*"

# Buffered wrappers for check-py: each suite's output is captured in a per-suite
# log file under $(PY_COV_DIR); exit codes land in a matching .rc file. check-py
# replays the logs sequentially after all suites finish, so parallel pytest
# output never interleaves. pysuite/% is kept unbuffered for direct invocation
# (e.g. `make pysuite/tools`) and pin tests.
PY_SUITE_BUF_TARGETS := $(addprefix pysuite-buf/,$(PY_TEST_SUITES))
.PHONY: $(PY_SUITE_BUF_TARGETS)
$(PY_SUITE_BUF_TARGETS): pysuite-buf/%:
	@mkdir -p "$(CURDIR)/$(PY_COV_DIR)"
	@{ echo "  → $*"; \
	   COVERAGE_FILE="$(CURDIR)/$(PY_COV_DIR)/.coverage.$(subst /,_,$*)" \
	     $(PYTHON) -m pytest -q -p no:cacheprovider --color=yes --cov --cov-report= "$*"; \
	} > "$(CURDIR)/$(PY_COV_DIR)/log.$(subst /,_,$*)" 2>&1; \
	echo "$$?" > "$(CURDIR)/$(PY_COV_DIR)/rc.$(subst /,_,$*)"

check-py:
	@echo "🐍 Running Python Test Suite (with coverage, parallel)..."
	@COVDIR=$$(mktemp -d .coverage-tmp.XXXXXX); \
	$(MAKE) -j$(JOBS) -k $(PY_SUITE_BUF_TARGETS) PY_COV_DIR="$$COVDIR" 2>/dev/null; \
	$(PYTHON) tools/format_pytest_output.py "$$COVDIR" "$(PY_TEST_SUITES)"; \
	FAIL=$$?; \
	echo ""; \
	echo "📊 Combined Python coverage:"; \
	$(PYTHON) -m coverage combine "$$COVDIR"; \
	COV=0; $(PYTHON) -m coverage report -m --fail-under=75 || COV=$$?; \
	rm -rf "$$COVDIR"; \
	if [ "$$FAIL" != "0" ]; then echo "❌ Python tests failed"; exit 1; fi; \
	if [ "$$COV" != "0" ]; then echo "❌ Python coverage below the 75% whole-suite floor"; exit 1; fi; \
	echo "✅ Python tests complete"

# Rank source files by coverage so Testpilot targets the highest-leverage files
# instead of eyeballing a truncated table. Regenerates fresh Python + JS coverage
# artifacts under coverage/ (gitignored), then ranks them. Default order is
# "quickwin" (fewest uncovered statements first) so each autonomous daily run
# finishes the most files to 100% and progress compounds toward full coverage.
#   make coverage-rank                   # quick wins first, all files below 100%
#   make coverage-rank LIMIT=5           # the 5 quickest wins
#   make coverage-rank ORDER=coverage    # lowest percent first
#   make coverage-rank ORDER=surface     # biggest uncovered bundles first
coverage-rank:
	@mkdir -p coverage/js
	@$(PYTHON) -m coverage erase
	@for suite in $(PY_TEST_SUITES); do \
		$(PYTHON) -m pytest -q --cov --cov-append --cov-report= "$$suite" >/dev/null 2>&1 || true; \
	done
	@$(PYTHON) -m coverage json -o coverage/py.json >/dev/null 2>&1 || true
	@COVDIR=$$(mktemp -d 2>/dev/null || mktemp -d -t c8cov); \
		NODE_V8_COVERAGE="$$COVDIR" COVERAGE_SUMMARY_DIR="coverage/js" \
		node tools/node_test_runner.mjs >/dev/null 2>&1 || true; \
		rm -rf "$$COVDIR"
	@$(PYTHON) tools/coverage_rank.py $(if $(LIMIT),--limit $(LIMIT),) $(if $(ORDER),--order $(ORDER),)

# -----------------------------------------------------------------------------
# Python Quality (ruff / black / mypy / bandit) — first-party code only.
# Tools are pinned in requirements-dev.txt; run `pip install -r requirements-dev.txt`
# (or activate the venv) first. Scope is controlled by pyproject.toml / mypy.ini /
# .bandit, so third-party addons are excluded automatically.
# -----------------------------------------------------------------------------

quality-py: lint-py fmt-py-check typecheck security-py complexity-py imports-py
	@echo "✅ Python quality checks complete"

lint-py:
	@$(PYTHON) -m ruff --version >/dev/null 2>&1 || { echo "⊘ ruff not installed (pip install -r requirements-dev.txt)"; exit 1; }
	@$(call CHECK_TOOL_VERSION,ruff)
	@echo "🐍 Ruff (lint)..."
	@$(PYTHON) -m ruff check $(PY_ALL)

fmt-py-check:
	@$(PYTHON) -m black --version >/dev/null 2>&1 || { echo "⊘ black not installed (pip install -r requirements-dev.txt)"; exit 1; }
	@$(call CHECK_TOOL_VERSION,black)
	@echo "🐍 Black (format check)..."
	@$(PYTHON) -m black --check $(PY_ALL)

fmt-py:
	@echo "🐍 Black (format) + Ruff (autofix)..."
	@$(PYTHON) -m black $(PY_ALL)
	@$(PYTHON) -m ruff check --fix $(PY_ALL)

typecheck:
	@$(PYTHON) -m mypy --version >/dev/null 2>&1 || { echo "⊘ mypy not installed (pip install -r requirements-dev.txt)"; exit 1; }
	@$(call CHECK_TOOL_VERSION,mypy)
	@echo "🐍 mypy (type check)..."
	@$(PYTHON) -m mypy $(PY_SRC)

security-py:
	@$(PYTHON) -m bandit --version >/dev/null 2>&1 || { echo "⊘ bandit not installed (pip install -r requirements-dev.txt)"; exit 1; }
	@$(call CHECK_TOOL_VERSION,bandit)
	@echo "🐍 Bandit (security, high severity)..."
	@$(PYTHON) -m bandit -rq -lll --ini .bandit $(PY_SRC)

# Complexity ratchet (docs/lint-and-quality.md): xenon fails if the
# average/worst cyclomatic-complexity rank regresses past these ceilings.
# Vendored trees (review_heatmap/libaddon, _vendor, _vendor_legacy) are excluded
# the same way ruff/black exclude them in pyproject.toml.
complexity-py:
	@$(PYTHON) -m xenon --version >/dev/null 2>&1 || { echo "⊘ xenon not installed (pip install -r requirements-dev.txt)"; exit 1; }
	@$(call CHECK_TOOL_VERSION,xenon)
	@echo "🐍 Xenon (complexity ratchet)..."
	@$(PYTHON) -m xenon --max-average A --max-modules F --max-absolute F \
		-e '*/libaddon/*,*/_vendor/*,*/_vendor_legacy/*' $(PY_ALL)

# Dependency-structure gate (docs/lint-and-quality.md): addons are
# self-contained — no cross-addon imports except the whitelisted optional
# integrations in pyproject.toml [tool.importlinter]. (No CHECK_TOOL_VERSION:
# unlike the formatters, import-linter's result does not drift with versions.)
imports-py:
	@$(PYTHON) -c "import importlinter" >/dev/null 2>&1 || { echo "⊘ import-linter not installed (pip install -r requirements-dev.txt)"; exit 1; }
	@echo "🐍 import-linter (addon independence)..."
	@# No `python -m importlinter` entry point exists (the package has no
	@# __main__); call the click command behind the `lint-imports` script.
	@$(PYTHON) -c "from importlinter.cli import lint_imports_command; lint_imports_command()"

# Mutation-testing scaffold (docs/lint-and-quality.md) — deliberately NOT part
# of VERIFY_GATE: a full run multiplies the suite runtime by the mutant count.
# mutmut works incrementally (cache: .mutmut-cache/, sandbox: mutants/) and is
# scoped to strip_html_tags via pyproject.toml [tool.mutmut]. The weekly
# mutation-testing.yml workflow runs this and uploads the kill report.
mutate-py:
	@$(PYTHON) -c "import mutmut" >/dev/null 2>&1 || { echo "⊘ mutmut not installed (pip install -r requirements-dev.txt)"; exit 1; }
	@echo "🧬 mutmut (strip_html_tags smoke scope, non-blocking)..."
	@$(PYTHON) -m mutmut run
	@$(PYTHON) -m mutmut results

# JS mutation testing was evaluated and skipped — Stryker cannot instrument
# this repo's tests. Evidence in docs/lint-and-quality.md ("Mutation testing").
mutate-js:
	@echo "⊘ mutate-js: Stryker not viable on this repo — see docs/lint-and-quality.md"
	@exit 1

# -----------------------------------------------------------------------------
# Pre-commit Checks
# -----------------------------------------------------------------------------

# The verification gate — the single source of truth for "is this commit-ready?".
# BOTH `precommit` (verify-only, what CI runs) and `precommit-fix` (fix-then-verify)
# reference this, so they can never silently diverge. Add a gate here once and it
# applies everywhere; CI runs `make precommit SKIP=1`.
VERIFY_GATE := fmt-check lint typecheck-js quality-py check sync-check

# Output buffering for the parallel verify gate: macOS ships GNU Make 3.81 which
# lacks --output-sync, so each gate member's output is captured in a log file
# under $(VERIFY_LOG_DIR). After all members finish (in parallel), `verify`
# replays them sequentially with pass/fail section headers. This eliminates
# interleaved output while preserving full parallelism.
#
# Real-time progress: each gate prints a one-line start/done indicator directly
# to the terminal (outside the redirected log), so the user sees live progress
# during the parallel run instead of a long silence.
VERIFY_LOG_DIR := .make/verify-logs
VERIFY_GATE_BUFFERED := $(addprefix vgate/,$(VERIFY_GATE))
.PHONY: $(VERIFY_GATE_BUFFERED)
$(VERIFY_GATE_BUFFERED): vgate/%:
	@mkdir -p $(VERIFY_LOG_DIR)
	@printf '  \033[2m⏳ %s ...\033[0m\n' "$*"
	@MAKEFLAGS= FORCE_COLOR=1 $(MAKE) $* > "$(VERIFY_LOG_DIR)/$*.log" 2>&1; \
	RC=$$?; echo "$$RC" > "$(VERIFY_LOG_DIR)/$*.rc"; \
	if [ "$$RC" = "0" ]; then \
		printf '  \033[32m✅ %s\033[0m\n' "$*"; \
	else \
		printf '  \033[31m❌ %s\033[0m\n' "$*"; \
	fi

verify:
	@echo ""
	@echo "⏳ Running verification gate (parallel)..."
	@rm -rf $(VERIFY_LOG_DIR) && mkdir -p $(VERIFY_LOG_DIR)
	@$(MAKE) -j$(JOBS) $(VERIFY_GATE_BUFFERED) 2>/dev/null; \
	FAIL=0; \
	for gate in $(VERIFY_GATE); do \
		rc=0; \
		if [ -f "$(VERIFY_LOG_DIR)/$$gate.rc" ]; then rc=$$(cat "$(VERIFY_LOG_DIR)/$$gate.rc"); fi; \
		if [ "$$rc" = "0" ]; then \
			printf '\n\033[32m━━━ ✅ %s ━━━\033[0m\n' "$$gate"; \
		else \
			printf '\n\033[31m━━━ ❌ %s ━━━\033[0m\n' "$$gate"; \
			FAIL=1; \
		fi; \
		if [ -f "$(VERIFY_LOG_DIR)/$$gate.log" ]; then cat "$(VERIFY_LOG_DIR)/$$gate.log"; fi; \
	done; \
	if [ "$$FAIL" != "0" ]; then exit 1; fi

precommit: $(if $(filter 1,$(SKIP_FETCH) $(SKIP)),,fetch-prompt) verify
	@echo ""
	@echo "✅ Pre-commit checks passed"

fetch-prompt:
	@echo ""
	@echo "📦 Fetch Anki stats before pre-commit? (y/n)"
	@read -r response && \
	if [ "$$response" = "y" ] || [ "$$response" = "yes" ]; then \
		$(MAKE) fetch; \
	else \
		echo "   ⊘ Fetch skipped"; \
	fi

# Fix-then-verify: auto-fix everything (fmt, lint-fix, fmt-py) and THEN run the exact
# same $(VERIFY_GATE) (via `verify`) as `precommit`, so a green precommit-fix means
# CI is green too.
#
# YOLO=1 overlaps the slow steps (R2 sync, graph exports — see
# docs/precommit-speed.md §4) with the fixers+gate instead of running
# everything serially: they're kicked off in the background right after
# fetch, fixers+gate run in the foreground, commit+push fires as soon as
# the gate+security scan are green (not waiting on the background jobs —
# approved policy, docs/precommit-speed.md §9), and the background jobs are
# wait-ed on and their logs printed last. A failed gate skips security-
# check/commit entirely, matching the old prerequisite-failure hard-stop;
# background jobs are still waited on and reported either way since they
# were already started.
# graph-local/graph-push write only gitignored files, so the early commit
# above never misses anything of theirs. The R2 upload is the ONE exception
# — it's the sole path that mutates a tracked file (data/cloudflare/
# hash_map.json, via save_hash_map() in data/anki/upload-to-r2, after a
# successful upload), so it can finish well after the main commit already
# ran. That's handled below with its own small follow-up commit right after
# the R2 job's `wait`, instead of blocking the main commit on it — losing
# hash_map.json (not committing it at all) isn't safe to do here: without a
# real hash map, upload-to-r2 treats every note as unseen and silently
# re-uploads everything (see docs/incremental-staging.md).
# Depends on the stamped install targets (not `install`), so an unchanged
# lockfile/requirements.txt skips npm ci/pip install on every invocation.
#
# Hard wall-clock cap for EACH backgrounded NETWORK job (R2 upload, public
# graph push). Their upload clients have per-request timeouts, but on a
# limited-bandwidth link bytes keep trickling so no timeout ever fires — the
# jobs crawl for hours and this recipe's `wait` hung "forever" (observed
# 2026-07-13). tools/run_with_deadline.py kills the job's process group at
# the deadline (exit 124 → BG_FAIL → loud non-zero exit); both uploads are
# incremental, so a rerun on a healthy network resumes where they got to.
# The two network jobs run under separate deadlines so a slow R2 upload does
# not starve the public graph push (or vice versa).
# Override per-invocation: make precommit-fix YOLO=1 NET_DEADLINE=3600
NET_DEADLINE ?= 1800

# The push goes through tools/git_push_retry.py (retries with backoff; falls
# back to pushing queued commits one at a time so each HTTP request stays
# small — a bare `git push` dies with HTTP 408 on a slow uplink, observed
# 2026-07-13). The commit step is skipped when the index is empty instead of
# aborting the chain, so a rerun after a failed push still retries the push.
# A failed commit/push flips PUSH_OK=0 and fails the target loudly — it used
# to be swallowed (exit 0 with the commit silently unpushed). Pinned by
# tests/test_makefile_push_gate.py.
#
# CAUTION: `make -n precommit-fix` is NOT a dry run. The recipe is one
# backslash-continued command containing `$(MAKE)`, and GNU make executes
# $(MAKE)-bearing recipe lines even under -n — so the REAL git add/commit/push
# step would run (only the recursive sub-makes go dry). The guard below makes
# -n/-q/-t refuse outright instead (bit an agent 2026-07-13: an attempted
# `make -n` syntax check created two junk commits). MAKEFLAGS packs the
# single-letter flags into its dash-less first word; long options like
# --no-print-directory are separate words and filtered out to avoid the 'n'
# in their names false-positiving. Pinned by tests/test_makefile_dryrun_guard.py.
# The check is parse-time (not a recipe line) because prerequisites like
# fetch-prompt-fix are themselves $(MAKE)-bearing and would execute — and
# block on a read prompt — before any recipe-line guard could fire.
PRECOMMIT_FIX_DRYRUN_FLAGS = $(filter-out --%,$(firstword $(MAKEFLAGS)))
PRECOMMIT_FIX_DRYRUN = $(findstring n,$(PRECOMMIT_FIX_DRYRUN_FLAGS))$(findstring q,$(PRECOMMIT_FIX_DRYRUN_FLAGS))$(findstring t,$(PRECOMMIT_FIX_DRYRUN_FLAGS))
ifneq (,$(PRECOMMIT_FIX_DRYRUN))
ifneq (,$(filter precommit-fix,$(MAKECMDGOALS)))
$(error make -n/-q/-t precommit-fix is NOT a dry run — the $$(MAKE)-bearing recipe would really commit and push. Refusing. Inspect the recipe text instead)
endif
endif
#
# CAUTION: the commit step below runs `git add -A`, which stages EVERYTHING
# in the working tree, not just what this invocation touched. If another
# process (a concurrent agent session sharing this checkout, a background
# task without worktree isolation) has unrelated uncommitted changes sitting
# here when YOLO=1/MSG= runs, they get swept into this commit under this
# commit's message. Check `git status` first. See AGENTS.md Gotchas.
precommit-fix: .make/pip.stamp .make/npm-ci.stamp $(if $(filter 1,$(SKIP_FETCH) $(SKIP)),,fetch-prompt-fix)
	@mkdir -p .make; \
	BG_GRAPHLOCAL_PID=; BG_NETWORK_PID=; \
	if [ "$(YOLO)" = "1" ] && [ -z "$(SKIP)" ]; then \
		echo ""; \
		echo "📊 Export local private Knowledge Graph data? auto-yes (YOLO, backgrounded)"; \
		$(MAKE) graph-local > .make/graph-local.log 2>&1 & BG_GRAPHLOCAL_PID=$$!; \
	fi; \
	if [ "$(YOLO)" = "1" ] && [ -z "$(SKIP_R2)" ] && [ -z "$(SKIP)" ]; then \
		echo "📤 Upload private content to R2, then push public graph? auto-yes (YOLO, backgrounded, ≤$(NET_DEADLINE)s per job)"; \
		$(PYTHON) tools/run_with_deadline.py --seconds $(NET_DEADLINE) -- sh -c '$(PYTHON) tools/run_with_deadline.py --seconds $(NET_DEADLINE) -- $(MAKE) fetch-r2-skip-fetch && $(PYTHON) tools/run_with_deadline.py --seconds $(NET_DEADLINE) -- $(MAKE) graph-push' > .make/network-pipeline.log 2>&1 & BG_NETWORK_PID=$$!; \
	fi; \
	GATE_OK=1; SEC_OK=1; PUSH_OK=1; \
	$(MAKE) fmt lint-fix fmt-py verify || GATE_OK=0; \
	if [ "$$GATE_OK" = "1" ]; then \
		if [ "$(YOLO)" != "1" ] && [ -z "$(SKIP)" ]; then $(MAKE) graph-local-prompt; fi; \
		echo ""; \
		echo "🔒 Running EXTREMELY RIGOROUS security check..."; \
		echo "   Scanning ALL files for private Anki data..."; \
		python3 data/anki/security_check.py || SEC_OK=0; \
		echo ""; \
		echo "✅ Pre-commit fix complete"; \
		echo "Review changes with: git diff"; \
		echo "Then commit with: git commit -m 'your message'"; \
		if [ "$(YOLO)" != "1" ] && [ -z "$(SKIP_R2)" ] && [ -z "$(SKIP)" ]; then \
			echo ""; \
			echo "📤 Upload private content to R2? (y/n)"; \
			read -r response && \
			if [ "$$response" = "y" ] || [ "$$response" = "yes" ]; then \
				$(MAKE) fetch-r2-skip-fetch; \
			fi; \
			echo ""; \
			echo "🌐 Push public Knowledge Graph data to R2? (y/n)"; \
			read -r response_graph && \
			if [ "$$response_graph" = "y" ] || [ "$$response_graph" = "yes" ]; then \
				$(MAKE) graph-push; \
			fi; \
		fi; \
		if [ "$$SEC_OK" = "1" ]; then \
			_msg="$(MSG)"; \
			if [ -z "$$_msg" ]; then _msg="chore: データ取得・整形・リント修正・テスト・グラフ更新"; fi; \
			_rebase_flag=""; \
			if [ "$(YOLO)" = "1" ] || [ -n "$(MSG)" ]; then _rebase_flag="--auto-rebase"; fi; \
			if [ "$(YOLO)" = "1" ] || [ -n "$(MSG)" ]; then \
				echo ""; \
				echo "📝 Committing: $$_msg"; \
				git add -A && \
				{ git diff --cached --quiet || git commit -m "$$_msg"; } && \
				echo "" && \
				echo "🚀 Pushing to remote..." && \
				$(PYTHON) tools/git_push_retry.py $$_rebase_flag && \
				echo "✅ Committed and pushed." || PUSH_OK=0; \
			fi; \
		fi; \
	else \
		echo ""; \
		echo "❌ Pre-commit checks failed — skipping security check and commit"; \
	fi; \
	BG_FAIL=0; \
	if [ -n "$$BG_GRAPHLOCAL_PID" ]; then \
		wait $$BG_GRAPHLOCAL_PID || BG_FAIL=1; \
		echo ""; echo "📊 Local graph export log:"; cat .make/graph-local.log; \
	fi; \
	if [ -n "$$BG_NETWORK_PID" ]; then \
		wait $$BG_NETWORK_PID || BG_FAIL=1; \
		echo ""; echo "📤 Network pipeline log:"; cat .make/network-pipeline.log; \
		if ! git diff --quiet -- data/cloudflare/hash_map.json 2>/dev/null; then \
			echo ""; \
			echo "📝 R2 upload updated the hash map (GUID->SHA256 only, no note content —"; \
			echo "   see docs/incremental-staging.md) — committing separately, since the main"; \
			echo "   commit above already ran before this background job finished:"; \
			git add data/cloudflare/hash_map.json && \
			git commit -m "chore: update R2 hash map after sync" && \
			$(PYTHON) tools/git_push_retry.py $$_rebase_flag && \
			echo "✅ Hash map committed and pushed." || \
			echo "⚠️  Failed to commit/push the updated hash map — it will be picked up by the next run's git add -A."; \
		fi; \
	fi; \
	if [ "$$GATE_OK" != "1" ] || [ "$$SEC_OK" != "1" ]; then exit 1; fi; \
	if [ "$$PUSH_OK" != "1" ]; then \
		echo "❌ Commit/push step failed — any commit created is safe locally;"; \
		echo "   rerun 'git push' (or python3 tools/git_push_retry.py) when the network recovers"; \
		exit 1; \
	fi; \
	if [ "$$BG_FAIL" != "0" ]; then \
		echo "❌ Background R2/graph job(s) failed or hit the $(NET_DEADLINE)s network deadline — see logs above;"; \
		echo "   rerun 'make fetch-r2-skip-fetch' / 'make graph-push' when the network recovers (uploads resume incrementally)"; \
		exit 1; \
	fi

fetch-prompt-fix:
	@echo ""
	@if [ "$(YOLO)" = "1" ]; then \
		echo "📦 Fetch Anki stats (GitHub + R2 staging)? auto-yes (YOLO)"; \
		$(MAKE) fetch-and-stage-r2; \
	else \
		echo "📦 Fetch Anki stats (GitHub + R2 staging)? (y/n)"; \
		read -r response && \
		if [ "$$response" = "y" ] || [ "$$response" = "yes" ]; then \
			$(MAKE) fetch-and-stage-r2; \
		else \
			echo "   ⊘ Fetch skipped"; \
		fi; \
	fi

# -----------------------------------------------------------------------------
# Formatting
# -----------------------------------------------------------------------------

fmt:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(PRETTIER_FILES))" ]; then \
		echo "Formatting files with Prettier..."; \
		NODE_OPTIONS="--max-old-space-size=4096" npx prettier --write --cache --log-level warn --ignore-path .gitignore $(PRETTIER_FILES); \
	else \
		echo "No Prettier or no files to format"; \
	fi

fmt-check:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(PRETTIER_FILES))" ]; then \
		echo "Checking formatting..."; \
		NODE_OPTIONS="--max-old-space-size=4096" npx prettier --check --cache --log-level warn --ignore-path .gitignore $(PRETTIER_FILES); \
	else \
		echo "No Prettier or no files to check"; \
	fi

# .claude/commands/ is generated from .agents/skills/ (the canonical source) by
# tools/sync_commands.py. Fail if regeneration is not a no-op (content hash of
# the tree before vs after), so the generated copy can never silently go stale.
# Comparing against git HEAD would false-fail on legitimate uncommitted syncs.
sync-check:
	@before=$$(find .claude/commands -type f | LC_ALL=C sort | xargs shasum | shasum | cut -d' ' -f1); \
	$(PYTHON) tools/sync_commands.py >/dev/null; \
	after=$$(find .claude/commands -type f | LC_ALL=C sort | xargs shasum | shasum | cut -d' ' -f1); \
	if [ "$$before" = "$$after" ]; then \
		echo "sync-check: .claude/commands is up to date"; \
	else \
		echo "sync-check FAIL: .claude/commands was stale and has been regenerated — commit the updated files (python3 tools/sync_commands.py)."; \
		exit 1; \
	fi

# -----------------------------------------------------------------------------
# Linting
# -----------------------------------------------------------------------------

lint: lint-js lint-css lint-md depcheck

# Dependency-structure gate (docs/lint-and-quality.md): no circular imports in
# js/. Rules live in .dependency-cruiser.cjs; alias resolution (#js/, #ui/) in
# .dependency-cruiser.webpack.cjs. Hanging off `lint` puts it in VERIFY_GATE,
# so CI (`make precommit SKIP=1`) executes it.
depcheck:
	@if command -v npx >/dev/null 2>&1; then \
		echo "Checking JS dependency structure (dependency-cruiser)..."; \
		npx dependency-cruiser js sw.js --config .dependency-cruiser.cjs; \
	else \
		echo "⊘ npx not found — skipping dependency-structure check"; \
	fi

# JS strict type check (tsc --checkJs on a small, incrementally-growing
# `include` whitelist in jsconfig.json; blocking — see
# docs/js-typing-strategy.md). Named typecheck-js, not type-js, to mirror the
# existing Python `typecheck` target.
typecheck-js:
	@if command -v npx >/dev/null 2>&1; then \
		if [ -f jsconfig.json ]; then \
			echo "JS type check (tsc --checkJs on whitelist)..."; \
			npx tsc -p jsconfig.json; \
		else \
			echo "⊘ No jsconfig.json found — skipping JS type check"; \
		fi; \
	fi

lint-js:
	@mkdir -p .make
	@if command -v npx >/dev/null 2>&1; then \
		if ls eslint.config.* .eslintrc* 2>/dev/null | grep -q .; then \
			echo "Linting JavaScript (ESLint, first-party only)..."; \
			npx eslint --cache --cache-location .make/eslintcache .; \
		else \
			echo "⊘ No ESLint config found — skipping JS lint"; \
		fi; \
	fi

lint-css:
	@mkdir -p .make
	@if command -v npx >/dev/null 2>&1; then \
		if ls .stylelintrc* stylelint.config.* 2>/dev/null | grep -q .; then \
			echo "Linting CSS (Stylelint, first-party only)..."; \
			npx stylelint --cache --cache-location .make/stylelintcache "**/*.css"; \
		else \
			echo "⊘ No Stylelint config found — skipping CSS lint"; \
		fi; \
	fi

lint-fix:
	@mkdir -p .make
	@if command -v npx >/dev/null 2>&1; then \
		if ls eslint.config.* .eslintrc* 2>/dev/null | grep -q .; then \
			echo "Fixing JS lint issues (ESLint)..."; \
			npx eslint --cache --cache-location .make/eslintcache . --fix || true; \
		fi; \
		if ls .stylelintrc* stylelint.config.* 2>/dev/null | grep -q .; then \
			echo "Fixing CSS lint issues (Stylelint)..."; \
			npx stylelint --cache --cache-location .make/stylelintcache "**/*.css" --fix || true; \
		fi; \
	fi
	@$(MAKE) lint-md-fix

lint-md:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(MD_FILES))" ]; then \
		echo "Linting Markdown files..."; \
		npx markdownlint-cli $(MD_FILES); \
	else \
		echo "No markdownlint or no MD files to lint"; \
	fi

lint-md-fix:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(MD_FILES))" ]; then \
		echo "Fixing Markdown issues..."; \
		npx markdownlint-cli --fix $(MD_FILES) || echo "Markdownlint could not fix all issues"; \
	else \
		echo "No markdownlint or no MD files to fix"; \
	fi

# -----------------------------------------------------------------------------
# Git Hooks
# -----------------------------------------------------------------------------

hooks:
	@echo "Installing git pre-commit hook..."
	@mkdir -p .git/hooks
	@echo '#!/bin/sh\nmake precommit' > .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Pre-commit hook installed"
	@echo "To remove: rm .git/hooks/pre-commit"
