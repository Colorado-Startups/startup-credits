#!/usr/bin/env python3
"""The repository's text checks, defined once. CI calls this file; anyone may run it before a commit.

  python3 -I tools/checks.py              check the tracked and new files of this repository
  python3 -I tools/checks.py --self-test  seeded trees that must pass and must fail

Checks:
  json     every *.json parses
  dash     no em dash and no en dash in any text file (house rule: a spaced en dash reads as an em dash)
  email    no email address in a text file, except reserved example domains (contact data never enters git)
  private  no file at a path this repository never holds, and no JSON key that starts with cs_ or is evidence: those
           stay in the private application repository (catalog/README.md says what is public)
Exit 0: clean. Exit 1: a finding. Exit 2: could not check (infrastructure, not a finding).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

DASHES = ("\u2014", "\u2013")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})")
EXAMPLE_DOMAINS = re.compile(r"(^|\.)(example\.(com|org|net)|[a-z0-9-]+\.invalid)$")
# Paths that stay private (the plan's always-private list): a file here is refused wherever it sits.
PRIVATE_NAMES = {"accounts.registry.json", "llc-restart.json", "keys.toml", "signins.toml", "recommendations.md",
                 "no-promote.json"}
PRIVATE_DIRS = {"local", "credit-applications", "applications", "partners"}


class CannotCheck(Exception):
    """Infrastructure, not a finding."""


def files(root):
    """In a git repository: tracked files plus untracked ones that are not ignored, so a run before `git add` sees what
    a commit would carry. Elsewhere (the self-test's seeded trees): every file."""
    if os.path.isdir(os.path.join(root, ".git")):
        out = subprocess.run(["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             capture_output=True)
        if out.returncode != 0:
            raise CannotCheck("git ls-files failed")
        return [p for p in out.stdout.decode().split("\0") if p]
    found = []
    for d, _, names in os.walk(root):
        found += [os.path.relpath(os.path.join(d, n), root) for n in names]
    return found


def private_keys(node, where):
    """Paths to every cs_* or evidence key, at any depth."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k.startswith("cs_") or k == "evidence":
                out.append(f"{where}.{k}")
            out += private_keys(v, f"{where}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += private_keys(v, f"{where}[{i}]")
    return out


def check(root):
    out = []
    for rel in files(root):
        parts = rel.split("/")
        if parts[-1] in PRIVATE_NAMES or PRIVATE_DIRS & set(parts[:-1]):
            out.append(f"private: {rel} is a path that stays in the private repository")
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            raw = f.read()
        if b"\0" in raw[:8000]:
            continue  # binary
        text = raw.decode("utf-8", errors="replace")
        if rel.endswith(".json"):
            try:
                doc = json.loads(text)
            except ValueError as e:
                out.append(f"json: {rel} does not parse ({e})")
            else:
                out += [f"private: {rel} has the key {k}" for k in private_keys(doc, "$")]
        for n, line in enumerate(text.splitlines(), 1):
            if any(d in line for d in DASHES):
                out.append(f"dash: {rel}:{n} has an em or en dash; use a comma, semicolon, period or parentheses")
            for m in EMAIL.finditer(line):
                if not EXAMPLE_DOMAINS.search(m.group(1).lower()):
                    out.append(f"email: {rel}:{n} has an email address; contact data stays out of git")
    return out


def self_test():
    cases = (  # name, {path: text}, the check that must fire (None: clean)
        ("a clean tree passes", {"README.md": "Plain text.\n", "a.json": '{"x": 1}\n'}, None),
        ("an em dash is found", {"README.md": "one \u2014 two\n"}, "dash"),
        ("an en dash is found", {"README.md": "one \u2013 two\n"}, "dash"),
        ("an email address is found", {"README.md": "write to someone" + "@" + "company.co\n"}, "email"),
        ("an example.com address is allowed", {"README.md": "a@example.com and b@test.invalid\n"}, None),
        ("JSON that does not parse is found", {"a.json": "{nope\n"}, "json"),
        ("a cs_ key is found", {"a.json": '{"rows": [{"id": "x", "cs_status": "open"}]}\n'}, "private"),
        ("an evidence key is found, nested", {"a.json": '{"rows": [{"t": {"evidence": []}}]}\n'}, "private"),
        ("a key that only contains cs_ passes", {"a.json": '{"docs_url": "x"}\n'}, None),
        ("a private file name is found", {"catalog/keys.toml": "x\n"}, "private"),
        ("a private folder is found", {"applications/aws.md": "draft\n"}, "private"),
        ("a local/ folder is found", {"local/notes.md": "x\n"}, "private"),
        ("a binary file is skipped", {"logo.png": "\0\u2014"}, None),
    )
    bad = 0
    for name, tree, want in cases:
        with tempfile.TemporaryDirectory() as d:
            for rel, text in tree.items():
                os.makedirs(os.path.dirname(os.path.join(d, rel)) or d, exist_ok=True)
                with open(os.path.join(d, rel), "w", encoding="utf-8") as f:
                    f.write(text)
            found = check(d)
        ok = (not found) if want is None else bool(found) and all(f.startswith(want + ":") for f in found)
        bad += not ok
        print(f"self-test: {'ok   ' if ok else 'WRONG'} {name}" + ("" if ok else f" (found {found})"))
    print(f"self-test: {len(cases) - bad} of {len(cases)} cases behave")
    return 1 if bad else 0


def main(argv):
    try:
        if argv[1:] == ["--self-test"]:
            return self_test()
        if argv[1:]:
            print(__doc__.split("\n\n")[1])
            return 2
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = check(root)
        for line in out:
            print(f"checks: {line}")
        print("checks: clean" if not out else f"checks: {len(out)} finding(s)")
        return 1 if out else 0
    except CannotCheck as e:
        print(f"checks: could not check: {e} (infrastructure, not a finding)")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
