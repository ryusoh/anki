.PHONY: help fetch check

help:
	@echo "Targets:"
	@echo "  fetch    Fetch Anki stats to Git-friendly format"
	@echo "  check    Run all tests"
	@echo "  check-data    Run data files structure test"
	@echo "  check-ranges  Run time range filters test"
	@echo "  check-commands Run command handler test"
	@echo "  check-legend  Run chart legend test"
	@echo "  check-trie    Run trie autocomplete test"

fetch:
	@python3 data/anki/fetch

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
