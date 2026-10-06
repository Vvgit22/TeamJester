#!/usr/bin/env bash
# Rebuild the TeamJester overview deck (PPTX + PDF + previews + ledger +
# presenter script) from the pinned TeamJester main worktree.
#
#   ./build.sh                                   # default deck
#   ./build.sh --new-batch <file> [--new-batch-name "Batch 4"] [--out NAME]
#   ./build.sh --verify [...]                    # first re-run main's code
#
# Environment overrides: MAIN (worktree), PY (deck python), PY310 (main's
# python 3.10 environment, only needed for --verify).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
MAIN="${MAIN:-/Users/raduvadanici/Downloads/teamjester_main_7f0048e}"
PY="${PY:-$HERE/../.venv/bin/python}"
PY310="${PY310:-/tmp/tj_venv310/bin/python}"
cd "$HERE"

if [[ "${1:-}" == "--verify" ]]; then
  shift
  "$PY310" -W ignore src/verify_main.py --repo "$MAIN" --scratch /tmp/tj_repro \
    --out provenance
fi

OUT="TeamJester_Algorithm_Overview"
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  [[ "${args[$i]}" == "--out" ]] && OUT="${args[$((i + 1))]}"
done

"$PY" src/deck_numbers.py --repo "$MAIN"
"$PY" -W ignore src/make_assets.py --repo "$MAIN" >/dev/null
"$PY" -W ignore src/build_deck.py --repo "$MAIN" "$@"
"$PY" src/check_deck.py --deck "$OUT"
