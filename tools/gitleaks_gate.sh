#!/bin/bash
# tools/gitleaks_gate.sh: the secret scan, defined once. tools/secret_scan.sh installs gitleaks 8.30.1 (checksum-pinned) and
# calls --self-test, then the scan. --staged is for a pre-commit hook; this repository wires none.
#
#   bash tools/gitleaks_gate.sh GITLEAKS               scan this repository's whole history
#   bash tools/gitleaks_gate.sh GITLEAKS --staged      scan the staged changes (the pre-commit hook)
#   bash tools/gitleaks_gate.sh GITLEAKS --self-test   seeded throwaway repositories that must pass, fail or warn
# GITLEAKS is a path or a command name.
#
# Exit 0: clean. Exit 1: a finding (values are redacted in the log), or a .gitleaks.toml in the scanned tree.
# Exit 2: could not verify (no binary, not a git repository, or gitleaks itself failed): an infrastructure problem,
# not a finding, and the message says so. It fails closed on purpose. gitleaks exits 1 on its own
# errors, so the scan asks for exit code 3 on a finding to tell the two apart.
#
# A pull request must not be able to weaken its own scan. gitleaks 8.30.1 (cmd/root.go) reads a config from
# --config, GITLEAKS_CONFIG, GITLEAKS_CONFIG_TOML or <source>/.gitleaks.toml, and suppressions from
# <source>/.gitleaksignore, from --gitleaks-ignore-path (default: the working directory) and from gitleaks:allow
# comments. So the gate unsets both variables, refuses a .gitleaks.toml, points the ignore path at the source, prints
# every .gitleaksignore line as a warning, and passes --ignore-gitleaks-allow. The rules are gitleaks' defaults.
set -u
here=$(cd "$(dirname "$0")" && pwd)
LEAK=3
infra(){ echo "gitleaks gate: could not verify: $* (infrastructure, not a finding)" >&2; exit 2; }
gl=$(command -v -- "${1:-}" 2>/dev/null || true)
[ -n "${1:-}" ] && [ -n "$gl" ] && [ -x "$gl" ] || infra "no gitleaks binary at '${1:-}'"

scan(){ # dir [--staged] -> 0 clean, 1 a finding or a config file, 2 could not verify
  local src=$1 line
  shift
  git -C "$src" rev-parse --git-dir >/dev/null 2>&1 || { echo "gitleaks gate: $src is not a git repository"; return 2; }
  if [ -e "$src/.gitleaks.toml" ]; then
    echo "gitleaks gate: $src/.gitleaks.toml exists. This repository scans with gitleaks' default rules only, because a config file could weaken them. Remove it."
    return 1
  fi
  if [ -f "$src/.gitleaksignore" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in "" | \#*) continue ;; esac
      echo "::warning::suppressed by .gitleaksignore: $line"
    done < "$src/.gitleaksignore"
  fi
  env -u GITLEAKS_CONFIG -u GITLEAKS_CONFIG_TOML "$gl" git "$@" --redact --verbose --no-banner --ignore-gitleaks-allow \
    --gitleaks-ignore-path "$src" --exit-code "$LEAK" "$src"
  case $? in 0) return 0 ;; "$LEAK") return 1 ;; *) return 2 ;; esac
}

self_test(){
  local rc bad=0 dummy name want case_dir
  w=$(mktemp -d); trap 'rm -rf "$w"' EXIT   # global: the trap runs after this function returns
  seed(){ # dir file text: a repository with one commit
    mkdir -p "$1" && git -C "$1" init -q && printf '%s\n' "$3" > "$1/$2" && git -C "$1" add -A &&
      git -C "$1" -c user.name=self-test -c user.email=self-test@example.invalid -c commit.gpgsign=false commit -qm seed
  }
  # a GitHub token's shape (gitleaks rule github-pat), random, made here at run time and never written to this repo
  dummy=ghp_$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 36)
  [ ${#dummy} = 40 ] || infra "could not make the dummy"
  {
    seed "$w/seeded" settings.txt "token = $dummy" &&
    seed "$w/clean" notes.txt "nothing secret here" &&
    seed "$w/allowed" settings.txt "token = $dummy # gitleaks:allow" &&
    seed "$w/envconfig" settings.txt "token = $dummy" &&
    mkdir -p "$w/configured" && printf '[allowlist]\npaths = ['"'''.*'''"']\n' > "$w/configured/.gitleaks.toml" &&
    cp "$w/configured/.gitleaks.toml" "$w/allow-all.toml" &&
    seed "$w/configured" settings.txt "token = $dummy" &&
    mkdir -p "$w/ignored" && printf '# a comment, not printed\nabc123:notes.txt:generic-api-key:1\n' > "$w/ignored/.gitleaksignore" &&
    seed "$w/ignored" notes.txt "nothing secret here" &&
    seed "$w/staged" notes.txt "nothing secret here" && printf 'token = %s\n' "$dummy" > "$w/staged/settings.txt" &&
      git -C "$w/staged" add settings.txt &&
    mkdir -p "$w/notgit" && printf 'not a repository\n' > "$w/notgit/notes.txt"
  } >/dev/null || infra "could not seed the repositories"

  check(){ # name wanted-exit what: one line, ok or WRONG; a WRONG prints the log unless it holds the dummy
    if [ "$rc" = "$2" ]; then echo "self-test: ok    $1: $3"; return; fi
    echo "self-test: WRONG $1 exits $rc, wants $2 ($3)"; bad=1
    grep -qF -- "$dummy" "$w/$1.log" || sed 's/^/    | /' "$w/$1.log"
  }
  scan "$w/seeded" > "$w/seeded.log" 2>&1; rc=$?
  check seeded 1 "a seeded token is found"
  if grep -qF -- "$dummy" "$w/seeded.log"; then echo "self-test: WRONG seeded: the log prints the token"; bad=1
  else echo "self-test: ok    seeded: the token is redacted in the log"
  fi
  scan "$w/clean" > "$w/clean.log" 2>&1; rc=$?
  check clean 0 "a clean repository passes"
  scan "$w/allowed" > "$w/allowed.log" 2>&1; rc=$?
  check allowed 1 "a gitleaks:allow comment does not hide a token"
  GITLEAKS_CONFIG=$w/allow-all.toml GITLEAKS_CONFIG_TOML=$(cat "$w/allow-all.toml") scan "$w/envconfig" > "$w/envconfig.log" 2>&1; rc=$?
  check envconfig 1 "GITLEAKS_CONFIG and GITLEAKS_CONFIG_TOML are ignored"
  scan "$w/configured" > "$w/configured.log" 2>&1; rc=$?
  check configured 1 "a .gitleaks.toml in the tree is refused"
  scan "$w/ignored" > "$w/ignored.log" 2>&1; rc=$?
  check ignored 0 "a .gitleaksignore is allowed"
  if grep -qx '::warning::suppressed by .gitleaksignore: abc123:notes.txt:generic-api-key:1' "$w/ignored.log" &&
     ! grep -q 'a comment' "$w/ignored.log"; then echo "self-test: ok    ignored: each .gitleaksignore line is printed as a warning"
  else echo "self-test: WRONG ignored: the .gitleaksignore line was not printed as a warning"; sed 's/^/    | /' "$w/ignored.log"; bad=1
  fi
  scan "$w/staged" --staged > "$w/staged.log" 2>&1; rc=$?
  check staged 1 "a staged token is found by --staged"
  scan "$w/notgit" > "$w/notgit.log" 2>&1; rc=$?
  check notgit 2 "a directory that is not a git repository cannot be verified"
  [ $bad = 0 ] && echo "self-test: the gate behaves" || { echo "self-test: the gate is broken"; return 1; }
}

report(){ # the exit code of a scan -> a last line, and that exit code
  case $1 in
    0) echo "gitleaks gate: clean ($2)" ;;
    1) echo "gitleaks gate: refused ($2; above, values redacted). Remove the value from the history. A false positive goes in .gitleaksignore as its fingerprint, never a value" ;;
    *) infra "gitleaks did not finish the scan ($2)" ;;
  esac
  exit "$1"
}

echo "gitleaks gate: $("$gl" version 2>/dev/null || echo 'unknown version') at $gl"
case "${2:-}" in
  --self-test) self_test; exit ;;
  --staged) scan "$(git rev-parse --show-toplevel 2>/dev/null || pwd)" --staged; report $? "the staged changes" ;;
  "") scan "$(cd "$here/.." && pwd)"; report $? "the whole history" ;;
  *) sed -n '5,7p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
