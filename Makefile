.PHONY: help fetch fetch-r2 check precommit precommit-fix fmt fmt-check lint lint-fix hooks

PYTHON := python3
NPM := npm

# File patterns for formatters/linters (exclude vendor, data, and node_modules directories)
JS_FILES := $(shell git ls-files --cached --others --exclude-standard '*.js' 2>/dev/null | grep -v '^js/vendor/' | grep -v '^data/' | grep -v 'node_modules')
CSS_FILES := $(shell git ls-files --cached --others --exclude-standard '*.css' 2>/dev/null)
MD_FILES := $(shell git ls-files --cached --others --exclude-standard '*.md' 2>/dev/null)
HTML_FILES := $(shell git ls-files --cached --others --exclude-standard '*.html' 2>/dev/null)
JSON_FILES := $(shell git ls-files --cached --others --exclude-standard '*.json' 2>/dev/null | grep -v '^data/' | grep -v 'package-lock.json' | grep -v 'custom_stats_data.json' | grep -v 'review_stats_data.json')
PRETTIER_FILES := $(JS_FILES) $(CSS_FILES) $(MD_FILES) $(HTML_FILES) $(JSON_FILES)

help:
	@echo "Targets:"
	@echo "  fetch          Fetch Anki stats to Git-friendly format"
	@echo "  fetch-r2       Upload private Anki content to Cloudflare R2"
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

fetch-and-stage-r2:
	@echo "📦 Fetching Anki data (GitHub + R2 staging)..."
	@python3 data/anki/fetch --stage-r2
	@echo "✅ GitHub data exported + R2 files staged"

fetch-r2-skip-fetch:
	@echo "📤 Uploading already-staged R2 files (with sync)..."
	@python3 data/anki/upload-to-r2 --upload-only --sync --verbose

fetch-r2:
	@echo "📤 Uploading private Anki content to Cloudflare R2..."
	@python3 data/anki/upload-to-r2 --sync --verbose

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

check: check-data check-ranges check-commands check-legend check-trie check-timerange check-reviews check-debounce check-host check-date

check-debounce:
	@node tests/debounce.test.js

check-host:
	@node tests/host.test.js

check-date:
	@node tests/date.test.js

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

check-timerange:
	@node tests/timeRange.test.js

check-reviews:
	@node tests/reviews.test.js

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

precommit-fix: $(if $(filter 1,$(SKIP_FETCH) $(SKIP)),,fetch-prompt-fix) fmt lint-fix check
	@echo ""
	@echo "✅ Pre-commit fix complete"
	@echo "Review changes with: git diff"
	@echo "Then commit with: git commit -m 'your message'"
	@if [ -z "$(SKIP_R2)" ] && [ -z "$(SKIP)" ]; then \
		echo ""; \
		echo "📤 Upload private content to R2? (y/n)"; \
		read -r response && \
		if [ "$$response" = "y" ] || [ "$$response" = "yes" ]; then \
			$(MAKE) fetch-r2-skip-fetch; \
		fi; \
	fi

fetch-prompt-fix:
	@echo ""
	@echo "📦 Fetch Anki stats (GitHub + R2 staging)? (y/n)"
	@read -r response && \
	if [ "$$response" = "y" ] || [ "$$response" = "yes" ]; then \
		$(MAKE) fetch-and-stage-r2; \
	else \
		echo "   ⊘ Fetch skipped"; \
	fi

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
