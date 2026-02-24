.PHONY: help fetch check precommit precommit-fix fmt fmt-check lint lint-fix hooks

PYTHON := python3
NPM := npm

# File patterns for formatters/linters (exclude vendor, data, and node_modules directories)
JS_FILES := $(shell git ls-files '*.js' 2>/dev/null | grep -v '^js/vendor/' | grep -v '^data/' | grep -v 'node_modules')
CSS_FILES := $(shell git ls-files '*.css' 2>/dev/null)
MD_FILES := $(shell git ls-files '*.md' 2>/dev/null)
HTML_FILES := $(shell git ls-files '*.html' 2>/dev/null)
JSON_FILES := $(shell git ls-files '*.json' 2>/dev/null | grep -v '^data/' | grep -v 'package-lock.json' | grep -v 'custom_stats_data.json' | grep -v 'review_stats_data.json')
PRETTIER_FILES := $(JS_FILES) $(CSS_FILES) $(MD_FILES) $(HTML_FILES) $(JSON_FILES)

help:
	@echo "Targets:"
	@echo "  fetch          Fetch Anki stats to Git-friendly format"
	@echo "  check          Run all tests"
	@echo "  precommit      Run all pre-commit checks (no fixes)"
	@echo "  precommit-fix  Auto-fix issues and run pre-commit checks"
	@echo "  fmt            Format code (Prettier)"
	@echo "  fmt-check      Check formatting (dry-run)"
	@echo "  lint           Run linters (ESLint if available)"
	@echo "  lint-fix       Auto-fix lint issues"
	@echo "  hooks          Install git pre-commit hook"

# -----------------------------------------------------------------------------
# Data Fetching
# -----------------------------------------------------------------------------

fetch:
	@python3 data/anki/fetch

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

check: check-data check-ranges check-commands check-legend check-trie

check-data:
	@node tests/data_files.test.js

check-ranges:
	@node tests/terminal_time_ranges.test.js

check-commands:
	@node tests/commands.test.js

check-legend:
	@node tests/legend.test.js

check-trie:
	@node tests/trie.test.js

# -----------------------------------------------------------------------------
# Pre-commit Checks
# -----------------------------------------------------------------------------

precommit: fmt-check lint check
	@echo ""
	@echo "✅ Pre-commit checks passed"

precommit-fix: fetch fmt lint-fix check
	@echo ""
	@echo "✅ Pre-commit fix complete"
	@echo "Review changes with: git diff"
	@echo "Then commit with: git commit -m 'your message'"

# -----------------------------------------------------------------------------
# Formatting
# -----------------------------------------------------------------------------

fmt:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(PRETTIER_FILES))" ]; then \
		echo "Formatting files with Prettier..."; \
		npx prettier --write --log-level warn --ignore-path .gitignore $(PRETTIER_FILES); \
	else \
		echo "No Prettier or no files to format"; \
	fi

fmt-check:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(PRETTIER_FILES))" ]; then \
		echo "Checking formatting..."; \
		npx prettier --check --log-level warn --ignore-path .gitignore $(PRETTIER_FILES); \
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
	else \
		echo "No ESLint or no JS files to lint"; \
	fi

lint-fix:
	@if command -v npx >/dev/null 2>&1 && [ -n "$(strip $(JS_FILES))" ]; then \
		echo "Fixing lint issues..."; \
		npx eslint --fix $(JS_FILES) 2>/dev/null || echo "ESLint not configured or no issues"; \
	else \
		echo "No ESLint or no JS files to fix"; \
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
