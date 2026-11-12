#!/bin/bash
# tools/secret_scan.sh: CI's secret scan. Installs gitleaks 8.30.1 by checksum, fetches the full history (the CI
# checkout is shallow), proves the gate with its self-test, then scans every commit.
#   bash tools/secret_scan.sh
# Exit codes are tools/gitleaks_gate.sh's: 0 clean, 1 a finding, 2 could not verify.
set -euo pipefail
VERSION=8.30.1
SHA256_X64=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
SHA256_ARM64=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080
here=$(cd "$(dirname "$0")" && pwd)
case "$(uname -m)" in
  x86_64) arch=x64; sum=$SHA256_X64 ;;
  aarch64 | arm64) arch=arm64; sum=$SHA256_ARM64 ;;
  *) echo "secret scan: could not verify: no pinned gitleaks for $(uname -m) (infrastructure)" >&2; exit 2 ;;
esac
w=$(mktemp -d); trap 'rm -rf "$w"' EXIT
curl -fsSL -o "$w/gl.tgz" "https://github.com/gitleaks/gitleaks/releases/download/v$VERSION/gitleaks_${VERSION}_linux_$arch.tar.gz" ||
  { echo "secret scan: could not verify: the gitleaks download failed (infrastructure)" >&2; exit 2; }
echo "$sum  $w/gl.tgz" | sha256sum -c - >/dev/null ||
  { echo "secret scan: could not verify: the gitleaks checksum does not match (infrastructure)" >&2; exit 2; }
tar -xzf "$w/gl.tgz" -C "$w" gitleaks
if [ "$(git -C "$here/.." rev-parse --is-shallow-repository)" = true ]; then
  git -C "$here/.." fetch --quiet --unshallow
fi
bash "$here/gitleaks_gate.sh" "$w/gitleaks" --self-test
bash "$here/gitleaks_gate.sh" "$w/gitleaks"
