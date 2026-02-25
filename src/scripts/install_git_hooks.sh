#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK_SRC="${REPO_ROOT}/src/scripts/git-hooks/pre-commit"
HOOK_DST="${REPO_ROOT}/.git/hooks/pre-commit"

if [ ! -f "${HOOK_SRC}" ]; then
  echo "[hooks] source hook not found: ${HOOK_SRC}"
  exit 1
fi

if [ ! -d "${REPO_ROOT}/.git/hooks" ]; then
  echo "[hooks] .git/hooks not found under ${REPO_ROOT}"
  exit 1
fi

install -m 0755 "${HOOK_SRC}" "${HOOK_DST}"
echo "[hooks] installed pre-commit -> ${HOOK_DST}"
