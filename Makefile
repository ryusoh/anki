.PHONY: help fetch

help:
	@echo "Targets:"
	@echo "  fetch    Fetch Anki stats to Git-friendly format"

fetch:
	@python3 data/anki/fetch
