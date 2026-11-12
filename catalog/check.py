#!/usr/bin/env python3
"""The guard on catalog/programs.json: public fields only, first-party links, plain text, canonical bytes.

  python3 -I catalog/check.py              check programs.json; writes nothing
  python3 -I catalog/check.py --fix        check, then rewrite programs.json in canonical order and format
  python3 -I catalog/check.py --self-test  seeded rows that must pass and must fail; no files touched

programs.json is the one source of program facts, edited by pull request. Each row holds exactly ROW_FIELDS: an
allowlist, so a private column (a `cs_*` status, `evidence`, a note) is refused by default, not by a block list.
The allowlist and the text rules are ported from the private compute repository's free-compute/build_public.py
(read 2026-11-12); this file is now the definition.

Exit 0: clean. Exit 1: a finding. Exit 2: could not check (a missing or unreadable file: infrastructure).
"""
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "programs.json")

TOP_KEYS = ("version", "about", "checked", "buckets", "rows")
ROW_FIELDS = ("id", "program", "provider", "bucket", "credit_first", "credit_first_computed", "credit_max",
              "credit_max_computed", "amount_note", "covers", "requirements", "max_age_years", "funding_rule",
              "term", "traps", "link", "source", "checked", "apply_steps")
TRAP_FIELDS = ("card_required", "expiry", "overage", "trains_on_data", "other")
BUCKETS = ("no_incorporation", "incorporated", "funded_or_partner")
COVERS = {"cpu", "gpu", "inference", "other"}
OVERAGE = {"bills", "stops", "unknown", None}
ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
DASHES = ("\u2014", "\u2013")  # em and en dash: a spaced en dash reads as an em dash
# A sentence with our own arithmetic must say so, or a reader credits the sum to the provider.
COMPUTED = re.compile(r"\bsum\b|buys about|that is \$|twelve months", re.I)
COMPUTED_LABEL = "(computed here)"
SENTENCE = re.compile(r"(?<=[.;])\s+")
STEPS_MIN, STEPS_MAX, STEP_WORDS = 2, 5, 25


class CannotCheck(Exception):
    """Infrastructure, not a finding."""


def is_money(v):
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0)


def strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from strings(x)


def keys(v):
    """Every object key at any depth, so a private key nested anywhere is seen."""
    if isinstance(v, dict):
        for k, x in v.items():
            yield k
            yield from keys(x)
    elif isinstance(v, list):
        for x in v:
            yield from keys(x)


def text_list(v, allow_empty=True):
    return isinstance(v, list) and (allow_empty or v) and all(isinstance(s, str) and s.strip() for s in v)


def check_row(row, where):
    if not isinstance(row, dict):
        return [f"{where}: not an object"]
    out = []
    extra, missing = set(row) - set(ROW_FIELDS), set(ROW_FIELDS) - set(row)
    if extra:
        out.append(f"{where}: fields outside the public allowlist: {sorted(extra)}")
    if missing:
        out.append(f"{where}: missing fields: {sorted(missing)}")
    if not ID.match(str(row.get("id", ""))):
        out.append(f"{where}: id is not a lowercase slug")
    for k in ("program", "provider", "amount_note"):
        if not isinstance(row.get(k), str) or not row[k].strip():
            out.append(f"{where}: {k} is not text")
    if row.get("bucket") not in BUCKETS:
        out.append(f"{where}: bucket {row.get('bucket')!r} is not one of {list(BUCKETS)}")
    for k in ("credit_first", "credit_max"):
        if not is_money(row.get(k)):
            out.append(f"{where}: {k} is not a USD number or null")
    for k in ("credit_first_computed", "credit_max_computed"):
        if not isinstance(row.get(k), bool):
            out.append(f"{where}: {k} is not true or false")
    first, top = row.get("credit_first"), row.get("credit_max")
    if is_money(first) and is_money(top) and first is not None and top is not None and first > top:
        out.append(f"{where}: credit_first is above credit_max")
    covers = row.get("covers")
    if not isinstance(covers, list) or not covers or not set(covers) <= COVERS:
        out.append(f"{where}: covers is not a non-empty list from {sorted(COVERS)}")
    if not text_list(row.get("requirements"), allow_empty=False):
        out.append(f"{where}: requirements is not a non-empty list of text")
    age = row.get("max_age_years")
    if age is not None and (not isinstance(age, int) or isinstance(age, bool) or age <= 0):
        out.append(f"{where}: max_age_years is not a positive whole number or null")
    if not isinstance(row.get("funding_rule"), str):
        out.append(f"{where}: funding_rule is not text (match/match.py --check-catalog holds the vocabulary)")
    if row.get("term") is not None and not isinstance(row.get("term"), str):
        out.append(f"{where}: term is not text or null")
    traps = row.get("traps")
    if not isinstance(traps, dict):
        out.append(f"{where}: traps is not an object")
    else:
        if set(traps) != set(TRAP_FIELDS):
            out.append(f"{where}: traps fields are not exactly {list(TRAP_FIELDS)}")
        for k in ("card_required", "trains_on_data"):
            if traps.get(k) not in (True, False, None):
                out.append(f"{where}: traps.{k} is not true, false or null")
        if traps.get("overage") not in OVERAGE:
            out.append(f"{where}: traps.overage is not bills, stops, unknown or null")
        if not text_list(traps.get("other")):
            out.append(f"{where}: traps.other is not a list of text")
    for k in ("link", "source"):
        if not str(row.get(k) or "").startswith("https://"):
            out.append(f"{where}: {k} is not an https URL")
    if not DATE.match(str(row.get("checked") or "")):
        out.append(f"{where}: checked is not YYYY-MM-DD")
    steps = row.get("apply_steps")
    if not text_list(steps) or not STEPS_MIN <= len(steps) <= STEPS_MAX:
        out.append(f"{where}: apply_steps is not {STEPS_MIN} to {STEPS_MAX} steps of text")
    else:
        for n, s in enumerate(steps, 1):
            if len(s.split()) > STEP_WORDS:
                out.append(f"{where}: apply step {n} is over {STEP_WORDS} words")
    for s in strings(row):
        if any(d in s for d in DASHES):
            out.append(f"{where}: an em or en dash (use a comma, colon or parentheses)")
            break
    for s in strings(row):
        if EMAIL.search(s):
            out.append(f"{where}: an email address in a public field")
            break
    for s in strings(row):
        for sent in SENTENCE.split(s):
            if COMPUTED.search(sent) and COMPUTED_LABEL not in sent:
                out.append(f"{where}: arithmetic without {COMPUTED_LABEL}: {sent[:80]!r}")
    return out


def canonical(doc):
    """The document in canonical order: rows by bucket, provider, program. Same facts, same bytes."""
    rank = {b: i for i, b in enumerate(BUCKETS)}
    rows = sorted(doc["rows"], key=lambda r: (rank.get(r.get("bucket"), len(BUCKETS)),
                                              str(r.get("provider")).lower(), str(r.get("program")).lower()))
    out = {k: doc.get(k) for k in TOP_KEYS}
    out["rows"] = [{k: r.get(k) for k in ROW_FIELDS if k in r} | {k: v for k, v in r.items() if k not in ROW_FIELDS}
                   for r in rows]
    return out


def render(doc):
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def check_doc(doc, text=None):
    """Findings for the whole document. `text` is the file as read, for the canonical-bytes check."""
    if not isinstance(doc, dict):
        return ["programs.json is not a JSON object"]
    out = []
    if set(doc) != set(TOP_KEYS):
        out.append(f"top-level keys are not exactly {list(TOP_KEYS)}: {sorted(set(doc) ^ set(TOP_KEYS))}")
    if doc.get("version") != 1:
        out.append("version is not 1")
    if not isinstance(doc.get("about"), str):
        out.append("about is not text")
    if not DATE.match(str(doc.get("checked") or "")):
        out.append("top-level checked is not YYYY-MM-DD")
    if doc.get("buckets") != list(BUCKETS):
        out.append(f"buckets is not {list(BUCKETS)}")
    rows = doc.get("rows")
    if not isinstance(rows, list) or not rows:
        return out + ["rows is empty or not a list"]
    for k in keys(doc):
        if k.startswith("cs_") or k == "evidence":
            out.append(f"a private key {k!r} is in the document")
    seen = set()
    for i, row in enumerate(rows):
        rid = row.get("id") if isinstance(row, dict) else None
        where = f"row {i} ({rid or '?'})"
        out += check_row(row, where)
        if rid in seen:
            out.append(f"{where}: duplicate id")
        seen.add(rid)
        if isinstance(row, dict) and str(row.get("checked") or "") > str(doc.get("checked") or ""):
            out.append(f"{where}: checked is after the top-level checked date")
    if text is not None and not out and render(canonical(doc)) != text:
        out.append("programs.json is not in canonical order and format: run python3 -I catalog/check.py --fix")
    return out


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError as e:
        raise CannotCheck(f"{path} is missing") from e
    except (OSError, UnicodeDecodeError) as e:
        raise CannotCheck(f"{path} cannot be read ({e})") from e
    try:
        return json.loads(text), text
    except ValueError as e:
        return None, f"programs.json does not parse as JSON ({e})"


def run(path, fix=False):
    doc, text = load(path)
    if doc is None:
        return [text]
    out = check_doc(doc, None if fix else text)
    if fix and not out:
        with open(path, "w", encoding="utf-8") as f:
            f.write(render(canonical(doc)))
    return out


def self_test():
    good = {"id": "p1", "program": "Credits", "provider": "Acme", "bucket": "incorporated", "credit_first": 1000,
            "credit_first_computed": False, "credit_max": 5000, "credit_max_computed": False, "amount_note": "n",
            "covers": ["gpu"], "requirements": ["a company"], "max_age_years": 10, "funding_rule": "none",
            "term": "12 months", "traps": {"card_required": True, "expiry": "12 months", "overage": "bills",
                                           "trains_on_data": None, "other": []},
            "link": "https://acme.example/apply", "source": "https://acme.example/startups", "checked": "2026-11-12",
            "apply_steps": ["Open the apply page.", "Submit the form."]}

    def env(rows, **top):
        d = {"version": 1, "about": "a", "checked": "2026-11-12", "buckets": list(BUCKETS), "rows": rows}
        d.update(top)
        return d

    def v(**kw):
        r = json.loads(json.dumps(good))
        r.update(kw)
        return r

    def without(k):
        return {x: y for x, y in good.items() if x != k}

    def trap(**kw):
        return v(traps=dict(good["traps"], **kw))

    cases = [  # name, document, wants a finding
        ("a clean row passes", env([good]), False),
        ("a cs_status field is refused", env([v(cs_status="have")]), True),
        ("an evidence field is refused", env([v(evidence=[{"url": "https://acme.example", "quote": "q"}])]), True),
        ("a private key inside traps is refused", env([trap(cs_note="x")]), True),
        ("a private top-level key is refused", env([good], cs_summary="x"), True),
        ("a missing field is refused", env([without("apply_steps")]), True),
        ("a bad bucket fails", env([v(bucket="seed")]), True),
        ("a string amount fails", env([v(credit_max="$5,000")]), True),
        ("a first amount above the max fails", env([v(credit_first=9000)]), True),
        ("a missing computed flag fails", env([without("credit_max_computed")]), True),
        ("unlabeled arithmetic fails", env([v(amount_note="$30 a month; $360 is twelve months of it.")]), True),
        ("an unlabeled sum fails", env([v(amount_note="The total is the sum of the two caps.")]), True),
        ("labeled arithmetic passes",
         env([v(amount_note="$30 buys about 9 hours (computed here).", credit_max_computed=True)]), False),
        ("an em dash fails", env([v(amount_note="one \u2014 two")]), True),
        ("an en dash in a step fails", env([v(apply_steps=["Open it \u2013 now.", "Submit."])]), True),
        ("an email in a public field fails", env([v(requirements=["write to x" + "@" + "acme.example"])]), True),
        ("an http source fails", env([v(source="http://acme.example")]), True),
        ("an http link fails", env([v(link="http://acme.example/apply")]), True),
        ("one apply step is too few", env([v(apply_steps=["Apply."])]), True),
        ("six apply steps are too many", env([v(apply_steps=["Do it."] * 6)]), True),
        ("an apply step over 25 words fails", env([v(apply_steps=["word " * 26, "Submit."])]), True),
        ("an unknown cover fails", env([v(covers=["storage"])]), True),
        ("an unknown overage fails", env([trap(overage="maybe")]), True),
        ("a bad date fails", env([v(checked="12 Nov 2026")]), True),
        ("a row checked after the file date fails", env([v(checked="2026-12-01")]), True),
        ("a duplicate id fails", env([good, good]), True),
        ("an empty catalog fails", env([]), True),
        ("an uppercase id fails", env([v(id="P1")]), True),
    ]
    bad = 0
    for name, doc, want in cases:
        got = bool(check_doc(doc))
        ok = got == want
        bad |= not ok
        print(f"self-test: {'ok   ' if ok else 'WRONG'} {name}")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "programs.json")
        doc = env([v(id="p2", provider="Zed"), v(id="p0", provider="Ace", bucket="no_incorporation"), good])
        with open(p, "w", encoding="utf-8") as f:
            json.dump(doc, f)
        unsorted = bool(run(p))
        fixed = run(p, fix=True) == [] and run(p) == []
        with open(p, encoding="utf-8") as f:
            ids = [r["id"] for r in json.load(f)["rows"]]
        ok = unsorted and fixed and ids == ["p0", "p1", "p2"]
        bad |= not ok
        print(f"self-test: {'ok   ' if ok else 'WRONG'} a file out of order fails, and --fix sorts it by bucket")
        with open(p, "w", encoding="utf-8") as f:
            f.write("not json")
        ok = bool(run(p))
        bad |= not ok
        print(f"self-test: {'ok   ' if ok else 'WRONG'} bytes that are not JSON are a finding")
        try:
            run(os.path.join(d, "missing.json"))
            ok = False
        except CannotCheck:
            ok = True
        bad |= not ok
        print(f"self-test: {'ok   ' if ok else 'WRONG'} a missing file is infrastructure (exit 2), not a finding")
    print("self-test passed" if not bad else "self-test FAILED")
    return 1 if bad else 0


def main(argv):
    args = argv[1:]
    if args == ["--self-test"]:
        return self_test()
    if args not in ([], ["--fix"]):
        print(__doc__)
        return 2
    try:
        out = run(CATALOG, fix=bool(args))
    except CannotCheck as e:
        print(f"catalog: could not check ({e}); infrastructure, not a finding")
        return 2
    for line in out:
        print(f"catalog: {line}")
    if out:
        print(f"catalog: {len(out)} finding(s)")
        return 1
    with open(CATALOG, encoding="utf-8") as f:
        n = len(json.load(f)["rows"])
    print(f"catalog: clean, {n} programs{', rewritten in canonical form' if args else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
