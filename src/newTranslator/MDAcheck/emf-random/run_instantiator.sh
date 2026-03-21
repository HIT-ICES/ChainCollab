#!/usr/bin/env bash
set -euo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
uber="${here}/instantiator-uber.jar"

if [[ ! -f "${uber}" ]]; then
  "${here}/repack_instantiator_uberjar.sh" >/dev/null
fi

exec java -jar "${uber}" "$@"

