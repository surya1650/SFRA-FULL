#!/usr/bin/env bash
# Bring the upstream SFRA repository in as a read-only managed dependency.
#
# We do NOT track external/SFRA/ in our git tree (see .gitignore). The
# inventory of which primitives we keep / wrap / replace lives at
# external/INVENTORY.md.
#
# Re-run safely: if external/SFRA/ already exists this script fast-forwards
# to the recorded SHA; it never deletes engineer-modified files.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${ROOT}/external/SFRA"
PIN_FILE="${ROOT}/external/SFRA.sha"
UPSTREAM="${SFRA_UPSTREAM:-https://github.com/surya1650/SFRA.git}"

mkdir -p "${ROOT}/external"

if [ -d "${TARGET}/.git" ]; then
    echo "[setup-external] Updating existing clone at ${TARGET}"
    git -C "${TARGET}" fetch --quiet origin
else
    echo "[setup-external] Cloning ${UPSTREAM} -> ${TARGET}"
    git clone --quiet "${UPSTREAM}" "${TARGET}"
fi

if [ -f "${PIN_FILE}" ]; then
    PINNED="$(tr -d '[:space:]' < "${PIN_FILE}")"
    echo "[setup-external] Checking out pinned SHA ${PINNED}"
    git -C "${TARGET}" -c advice.detachedHead=false checkout --quiet "${PINNED}"
else
    echo "[setup-external] No external/SFRA.sha pin file present; staying on default branch"
    echo "                 To pin, run:"
    echo "                   git -C external/SFRA rev-parse HEAD > external/SFRA.sha"
fi

echo "[setup-external] Done."
echo "                 Inventory: external/INVENTORY.md"
echo "                 Upstream HEAD: $(git -C "${TARGET}" rev-parse --short HEAD)"
