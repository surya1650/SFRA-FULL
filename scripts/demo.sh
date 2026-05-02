#!/usr/bin/env bash
# End-to-end smoke demo: register a transformer, open a cycle, start a
# session, upload one reference + one tested .frax, run the analysis,
# fetch the PDF report, and print the verdict.
#
# Prereqs:
#   1. Backend running on http://localhost:8000 (e.g. `make dev` or
#      `docker compose up -d`).
#   2. An admin user exists. See docs/OPERATIONS.md §2.
#   3. jq + curl installed.
#
# Usage:
#   ADMIN_EMAIL=admin@aptransco.test \
#   ADMIN_PASSWORD=admin1234 \
#   bash scripts/demo.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_EMAIL="${ADMIN_EMAIL:-admin@aptransco.test}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin1234}"
SAMPLES_DIR="${SAMPLES_DIR:-external/SFRA/backend/samples}"

if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required (apt-get install jq)." >&2
    exit 1
fi
if [[ ! -f "${SAMPLES_DIR}/ref.frax" || ! -f "${SAMPLES_DIR}/test.frax" ]]; then
    echo "Sample fixtures not found. Run scripts/setup_external.sh first." >&2
    exit 1
fi

echo "1) Login as admin → JWT"
TOKEN=$(curl -sf -X POST "${BASE_URL}/api/auth/login" \
    -H 'content-type: application/x-www-form-urlencoded' \
    --data-urlencode "username=${ADMIN_EMAIL}" \
    --data-urlencode "password=${ADMIN_PASSWORD}" \
    | jq -r .access_token)
[[ -z "${TOKEN}" || "${TOKEN}" == "null" ]] && { echo "Login failed."; exit 1; }
echo "   token=${TOKEN:0:24}…"

auth=(-H "authorization: Bearer ${TOKEN}")

echo "2) Register transformer TR-DEMO"
TID=$(curl -sf -X POST "${BASE_URL}/api/transformers" "${auth[@]}" \
    -H 'content-type: application/json' \
    -d '{"serial_no":"TR-DEMO","transformer_type":"TWO_WINDING","nameplate_mva":100,"hv_kv":220,"lv_kv":33,"vector_group":"YNd11","substation":"SS-DEMO"}' \
    | jq -r .id)
echo "   transformer_id=${TID}"

echo "3) Open commissioning cycle"
CID=$(curl -sf -X POST "${BASE_URL}/api/transformers/${TID}/cycles" "${auth[@]}" \
    -H 'content-type: application/json' \
    -d "{\"intervention_type\":\"COMMISSIONING\",\"cycle_start_date\":\"$(date -I)\"}" \
    | jq -r .id)
echo "   cycle_id=${CID}"

echo "4) Start a routine session"
SID=$(curl -sf -X POST "${BASE_URL}/api/transformers/${TID}/sessions" "${auth[@]}" \
    -H 'content-type: application/json' \
    -d "{\"overhaul_cycle_id\":\"${CID}\",\"session_type\":\"ROUTINE\",\"session_date\":\"$(date -I)\",\"tested_by\":\"demo-script\"}" \
    | jq -r .id)
echo "   session_id=${SID}"

echo "5) Upload reference trace (ref.frax) for EEOC_HV_R"
curl -sf -X POST "${BASE_URL}/api/sessions/${SID}/upload" "${auth[@]}" \
    -F "role=REFERENCE" -F "combination_code=EEOC_HV_R" \
    -F "file=@${SAMPLES_DIR}/ref.frax" >/dev/null
echo "   uploaded ref.frax"

echo "6) Upload tested trace (test.frax) for EEOC_HV_R"
curl -sf -X POST "${BASE_URL}/api/sessions/${SID}/upload" "${auth[@]}" \
    -F "role=TESTED" -F "combination_code=EEOC_HV_R" \
    -F "file=@${SAMPLES_DIR}/test.frax" >/dev/null
echo "   uploaded test.frax"

echo "7) Run analysis (Mode 1 dispatch)"
ANALYSIS=$(curl -sf -X POST "${BASE_URL}/api/sessions/${SID}/analyse" "${auth[@]}")
echo "   $(echo "${ANALYSIS}" | jq -c '{n_results, mode_1: .mode_1_count, mode_2: .mode_2_count}')"

echo "8) Per-row verdict"
echo "${ANALYSIS}" | jq -r '.results[] | "   \(.severity)  mode=\(.mode)  combo_id=\(.combination_id)  ref=\(.reference_trace_id // "—" | .[0:8])  test=\(.tested_trace_id[0:8])"'

echo "9) Verify the audit hash chain (admin-only)"
curl -sf "${BASE_URL}/api/audit/verify" "${auth[@]}" | jq -c .

echo "10) Download PDF report → /tmp/sfra-demo.pdf"
curl -sf "${BASE_URL}/api/sessions/${SID}/report.pdf" "${auth[@]}" -o /tmp/sfra-demo.pdf
ls -lh /tmp/sfra-demo.pdf

echo "11) Download XLSX report → /tmp/sfra-demo.xlsx"
curl -sf "${BASE_URL}/api/sessions/${SID}/report.xlsx" "${auth[@]}" -o /tmp/sfra-demo.xlsx
ls -lh /tmp/sfra-demo.xlsx

echo
echo "Done. Open the PDF/XLSX or visit http://localhost (if frontend is up)."
echo "Use the Comparison tab to step through the analysis interactively."
