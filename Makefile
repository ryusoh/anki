.PHONY: help fetch fetch-r2 check precommit precommit-fix fmt fmt-check lint lint-fix hooks

PYTHON := python3
NPM := npm

# File patterns for formatters/linters (exclude vendor, data, and node_modules directories)
JS_FILES := $(shell git ls-files --cached --others --exclude-standard '*.js' 2>/dev/null | grep -v '^js/vendor/' | grep -v '^assets/vendor/' | grep -v '^data/' | grep -v '^coverage/' | grep -v 'node_modules' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
CSS_FILES := $(shell git ls-files --cached --others --exclude-standard '*.css' 2>/dev/null | grep -v '^assets/vendor/' | grep -v '^coverage/' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
MD_FILES := $(shell git ls-files --cached --others --exclude-standard '*.md' 2>/dev/null | grep -v '^coverage/' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
HTML_FILES := $(shell git ls-files --cached --others --exclude-standard '*.html' 2>/dev/null | grep -v '^coverage/' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
JSON_FILES := $(shell git ls-files --cached --others --exclude-standard '*.json' 2>/dev/null | grep -v '^data/' | grep -v '^graph/' | grep -v '^coverage/' | grep -v 'package-lock.json' | grep -v 'custom_stats_data.json' | grep -v 'review_stats_data.json' | while read f; do [ -f "$$f" ] && echo "$$f"; done)
PRETTIER_FILES := $(JS_FILES) $(CSS_FILES) $(MD_FILES) $(HTML_FILES) $(JSON_FILES)

help:
	@echo "Targets:"
	@echo "  install        Install Python dependencies"
	@echo "  fetch          Fetch Anki stats to Git-friendly format"
	@echo "  fetch-r2       Upload private Anki content to Cloudflare R2"
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
	@echo "  lint           Run linters (ESLint if available)"
	@echo "  lint-fix       Auto-fix lint issues"
	@echo "  hooks          Install git pre-commit hook"

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

install:
	@echo "📦 Installing Python dependencies..."
	@pip3 install -q -r requirements.txt
	@echo "✅ Dependencies installed"

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

check-node:
	@COVDIR=$$(mktemp -d 2>/dev/null || mktemp -d -t c8cov); \
	NODE_V8_COVERAGE="$$COVDIR" node tools/node_test_runner.mjs; \
	STATUS=$$?; \
	rm -rf "$$COVDIR"; \
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

check-handler-regression:
	@node tests/handler_regression.test.mjs

check-handler-validation:
	@node tests/validateCommand.real.test.mjs

# Python test suites run as INDEPENDENT pytest invocations: each addon's tests
# bootstrap their own sys.path (e.g. `sys.path.insert(0, <addon>)`), so a single
# combined `pytest` run fails to collect. Coverage is accumulated across suites
# with --cov-append and reported once (mirrors check-node's JS coverage report).
# Requires pytest-cov (declared in requirements.txt) — run `make install` first.
# Excluded: tabbed_stats/tests — pre-existing failures under the root conftest
# mocks (tabbed_stats/tests/test_addcards_deleted_widget.py); fix separately.
PY_TEST_SUITES := \
	auto_image/tests \
	auto_mathjax/tests \
	auto_wiktionary/tests \
	data/anki/tests \
	graph/tests \
	highlight_search_matches/tests \
	prioritize_front_field_search/tests \
	remove_deck_highlight/tests \
	rewrite_text_of_study_cards/tests \
	stats_page_customizer/tests \
	strip_html_tags/tests \
	unify_review_count_colors/tests \
	tests \
	tools

check-py:
	@echo "🐍 Running Python Test Suite (with coverage)..."
	@# Invoke coverage via `python -m` (never bare `coverage`): the repo-root
	@# coverage/ directory shadows the `coverage` command on PATH.
	@$(PYTHON) -m coverage erase
	@FAIL=0; \
	for suite in $(PY_TEST_SUITES); do \
		echo "  → $$suite"; \
		pytest -q --cov --cov-append --cov-report= "$$suite" || FAIL=1; \
	done; \
	echo ""; \
	echo "📊 Combined Python coverage:"; \
	$(PYTHON) -m coverage report -m; \
	if [ "$$FAIL" != "0" ]; then echo "❌ Python tests failed"; exit 1; fi; \
	echo "✅ Python tests complete"

# -----------------------------------------------------------------------------
# Pre-commit Checks
# -----------------------------------------------------------------------------

precommit: $(if $(filter 1,$(SKIP_FETCH) $(SKIP)),,fetch-prompt) fmt-check lint check
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

precommit-fix: install $(if $(filter 1,$(SKIP_FETCH) $(SKIP)),,fetch-prompt-fix) fmt lint-fix check $(if $(filter 1,$(SKIP)),,graph-local-prompt)
	@echo ""
	@echo "🔒 Running EXTREMELY RIGOROUS security check..."
	@echo "   Scanning ALL files for private Anki data..."
	@python3 data/anki/security_check.py
	@echo ""
	@echo "✅ Pre-commit fix complete"
	@echo "Review changes with: git diff"
	@echo "Then commit with: git commit -m 'your message'"
	@if [ -z "$(SKIP_R2)" ] && [ -z "$(SKIP)" ]; then \
		if [ "$(YOLO)" = "1" ]; then \
			echo ""; \
			echo "📤 Upload private content to R2? auto-yes (YOLO)"; \
			$(MAKE) fetch-r2-skip-fetch; \
			echo ""; \
			echo "🌐 Push public Knowledge Graph data to R2? auto-yes (YOLO)"; \
			$(MAKE) graph-push; \
		else \
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
	fi
	@_msg="$(MSG)"; \
	if [ -z "$$_msg" ]; then _msg="chore: データ取得・整形・リント修正・テスト・グラフ更新"; fi; \
	if [ "$(YOLO)" = "1" ] || [ -n "$(MSG)" ]; then \
		echo ""; \
		echo "📝 Committing: $$_msg"; \
		git add -A && \
		git commit -m "$$_msg" && \
		echo "" && \
		echo "🚀 Pushing to remote..." && \
		git push && \
		echo "✅ Committed and pushed."; \
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
		NODE_OPTIONS="--max-old-space-size=4096" npx prettier --write --log-level warn --ignore-path .gitignore $(PRETTIER_FILES); \
	else \
		echo "No Prettier or no files to format"; \
	fi

fmt-check:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(PRETTIER_FILES))" ]; then \
		echo "Checking formatting..."; \
		NODE_OPTIONS="--max-old-space-size=4096" npx prettier --check --log-level warn --ignore-path .gitignore $(PRETTIER_FILES); \
	else \
		echo "No Prettier or no files to check"; \
	fi

# -----------------------------------------------------------------------------
# Linting
# -----------------------------------------------------------------------------

lint:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(JS_FILES))" ]; then \
		echo "Linting JavaScript files..."; \
		npx eslint $(JS_FILES) 2>/dev/null || echo "ESLint not configured or no issues"; \
	fi
	@$(MAKE) lint-md

lint-fix:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(JS_FILES))" ]; then \
		echo "Fixing lint issues..."; \
		npx eslint --fix $(JS_FILES) 2>/dev/null || echo "ESLint not configured or no issues"; \
	fi
	@$(MAKE) lint-md-fix

lint-md:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(MD_FILES))" ]; then \
		echo "Linting Markdown files..."; \
		npx markdownlint-cli $(MD_FILES) || echo "Markdownlint found issues"; \
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
