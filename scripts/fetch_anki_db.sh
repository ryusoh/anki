#!/bin/bash
# Fetch and anonymize Anki collection database for analytics work
# Usage: ./fetch_anki_db.sh
# Output: data/anki/collection_anonymized.anki2 (safe for GitHub)

set -e

ANKI_PROFILE="LZ"
ANKI_DIR="/Users/lz/Library/Application Support/Anki2/${ANKI_PROFILE}"
DEST_DIR="/Users/lz/Library/Application Support/Anki2/addons21/data/anki"
TEMP_DB="${DEST_DIR}/collection.anki2"
OUTPUT_DB="${DEST_DIR}/collection_anonymized.anki2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📦 Fetching and anonymizing Anki collection database..."
echo "   Source: ${ANKI_DIR}/collection.anki2"
echo "   Output: ${OUTPUT_DB} (GitHub-safe)"
echo ""

# Create destination directory
mkdir -p "${DEST_DIR}"

# Copy the database temporarily
cp "${ANKI_DIR}/collection.anki2" "${TEMP_DB}"

# Run anonymization script
echo "🔒 Anonymizing (removing card content)..."
python3 "${SCRIPT_DIR}/anonymize_anki_db.py"

# Remove the temporary full database
rm -f "${TEMP_DB}"

echo ""
echo "✅ Done! Only anonymized database is preserved."
echo "   Safe to upload to GitHub: ${OUTPUT_DB}"
