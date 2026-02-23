.PHONY: help fetch test

help:
	@echo "Targets:"
	@echo "  fetch    Fetch Anki stats to Git-friendly format"
	@echo "  test     Run terminal time range filter tests"

fetch:
	@python3 data/anki/fetch

test:
	@node tests/terminal_time_ranges.test.js
