#!/usr/bin/env bash
set -euo pipefail

echo "============================================="
echo "  constitution-rag: Full Extraction Pipeline"
echo "============================================="
echo ""

# Check dependencies
python3 -c "import pdfplumber" 2>/dev/null || { echo "ERROR: pip install pdfplumber"; exit 1; }
python3 -c "from docx import Document" 2>/dev/null || { echo "ERROR: pip install python-docx"; exit 1; }

TOTAL=0
FAILED=0

run_step() {
    local step="$1"
    local script="$2"
    local output="$3"
    echo "--- Phase $step: $script ---"
    if python3 "$script"; then
        if [ -f "$output" ]; then
            COUNT=$(python3 -c "import json; print(len(json.load(open('$output'))))")
            echo "  OK: $COUNT chunks in $output"
            TOTAL=$((TOTAL + COUNT))
        else
            echo "  WARN: script ran but $output not found"
            FAILED=$((FAILED + 1))
        fi
    else
        echo "  FAIL: $script exited with error"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# norm_ru is pre-built JSON, just validate
echo "--- Phase 1a: norm_ru (pre-built) ---"
if [ -f "norm_ru_chunks.json" ]; then
    COUNT=$(python3 -c "import json; print(len(json.load(open('norm_ru_chunks.json'))))")
    echo "  OK: $COUNT chunks in norm_ru_chunks.json"
    TOTAL=$((TOTAL + COUNT))
else
    echo "  SKIP: norm_ru_chunks.json not found"
fi
echo ""

run_step "1b" "norm_kz_extract.py"          "norm_kz_chunks.json"
run_step "2a" "commentary_ru_extract.py"     "commentary_ru_chunks.json"
run_step "2b" "commentary_kz_extract.py"     "commentary_kz_chunks.json"
run_step "3a" "faq_kz_extract.py"            "faq_kz_chunks.json"
run_step "3b" "faq_ru_extract.py"            "faq_ru_chunks.json"
run_step "4a" "deprecated_kz_extract.py"     "deprecated_kz_chunks.json"
run_step "4b" "deprecated_ru_extract.py"     "deprecated_ru_chunks.json"

echo "============================================="
echo "  TOTAL CHUNKS: $TOTAL"
echo "  FAILED STEPS: $FAILED"
echo "============================================="

if [ $FAILED -gt 0 ]; then
    echo "WARNING: Some steps failed. Check output above."
    exit 1
else
    echo "All extraction steps completed successfully."
fi
