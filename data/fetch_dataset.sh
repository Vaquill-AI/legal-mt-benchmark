#!/usr/bin/env bash
# Download the WMT25 Legal Domain Test Suite (IIT Patna) from the upstream repo.
# We do NOT redistribute the dataset; this fetches it from the source.
#
# Upstream: https://github.com/helloboyn/WMT25-TS
# Paper:    https://aclanthology.org/2025.wmt-1.57
set -euo pipefail

DEST="$(dirname "$0")/wmt25-legal"
mkdir -p "$DEST"

echo "Fetching WMT25 Legal Domain Test Suite into $DEST ..."

# The upstream repo ships parallel EN / HI text files. Adjust paths if upstream
# reorganises. We expect: eng-hin-test.eng.txt and eng-hin-test.hin.txt
BASE="https://raw.githubusercontent.com/helloboyn/WMT25-TS/main"

for f in eng-hin-test.eng.txt eng-hin-test.hin.txt; do
  echo "  - $f"
  curl -fsSL "$BASE/$f" -o "$DEST/$f" || {
    echo "Could not fetch $f automatically."
    echo "Please download the EN/HI parallel files from $BASE and place them in $DEST"
    exit 1
  }
done

echo "Done. Lines:"
wc -l "$DEST"/eng-hin-test.eng.txt "$DEST"/eng-hin-test.hin.txt
