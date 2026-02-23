.PHONY: help fetch test

help:
	@echo "Targets:"
	@echo "  fetch    Fetch Anki stats to Git-friendly format"
	@echo "  test     Run all tests"
	@echo "  test-data    Run data files structure test"
	@echo "  test-ranges  Run time range filters test"
	@echo "  test-commands Run command handler test"

fetch:
	@python3 data/anki/fetch

test: test-data test-ranges test-commands

test-data:
	@node tests/data_files.test.js

test-ranges:
	@node tests/terminal_time_ranges.test.js

test-commands:
	@node tests/commands.test.js
