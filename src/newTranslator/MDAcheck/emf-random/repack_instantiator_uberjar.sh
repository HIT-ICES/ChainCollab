#!/usr/bin/env bash
set -euo pipefail

here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
src_jar="${here}/instantiator-fatjar.jar"
out_jar="${here}/instantiator-uber.jar"

if [[ ! -f "${src_jar}" ]]; then
  echo "Missing ${src_jar}" >&2
  exit 1
fi

workdir="$(mktemp -d)"
cleanup() { rm -rf "${workdir}"; }
trap cleanup EXIT

mkdir -p "${workdir}/work"
cd "${workdir}/work"

jar xf "${src_jar}"

shopt -s nullglob
embedded_jars=( *.jar )

for j in "${embedded_jars[@]}"; do
  jar xf "${j}"
done

rm -f -- "${embedded_jars[@]}"

# Remove signing metadata that can break "java -jar" after repackaging.
rm -f META-INF/*.SF META-INF/*.RSA META-INF/*.DSA 2>/dev/null || true

# Remove the jar-in-jar bootstrap classes (not needed for an uber jar).
rm -rf org/eclipse/jdt/internal/jarinjarloader 2>/dev/null || true

cat > "${workdir}/MANIFEST.MF" <<'EOF'
Manifest-Version: 1.0
Main-Class: fr.inria.atlanmod.instantiator.Launcher
EOF

jar cfm "${out_jar}" "${workdir}/MANIFEST.MF" -C "${workdir}/work" .

echo "Wrote ${out_jar}"

