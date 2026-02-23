#!/bin/bash
# Fetch Anki data and export to Git-friendly format
# Usage: ./fetch_anki_db.sh
# Output: data/anki/*.json.gz (safe for GitHub)

set -e

ANKI_PROFILE="LZ"
ANKI_DIR="/Users/lz/Library/Application Support/Anki2/${ANKI_PROFILE}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DB="${SCRIPT_DIR}/collection.anki2"

echo "📦 Fetching Anki collection database..."
echo "   Source: ${ANKI_DIR}/collection.anki2"
echo "   Output: ${SCRIPT_DIR} (Git-friendly JSON)"
echo ""

# Copy the database temporarily
cp "${ANKI_DIR}/collection.anki2" "${TEMP_DB}"

# Run export script
echo "📊 Exporting to Git-friendly format..."
python3 "${SCRIPT_DIR}/export_for_git.py"

# Remove the temporary full database
rm -f "${TEMP_DB}"
rm -f "${TEMP_DB}-shm" "${TEMP_DB}-wal"

echo ""
echo "✅ Done! Files are safe to commit to GitHub."
echo ""
echo "📝 To commit:"
echo "   git add data/anki/"
echo "   git commit -m 'Update Anki stats'"
