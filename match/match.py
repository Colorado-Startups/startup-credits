#!/usr/bin/env python3
"""Match a startup's profile to the catalog programs it can get into, citing each program's requirements.

  python3 -I match/match.py PROFILE.json            the short list: what to apply for, with the steps
  python3 -I match/match.py PROFILE.json --json     the same as JSON
  python3 -I match/match.py --check-catalog         every catalog row has what this script reads (CI)
  python3 -I match/match.py --self-test             seeded profiles and programs that must match, need a check, or fail

Stdlib only. The catalog is catalog/programs.json (catalog/README.md). match/README.md has the profile shape.

Three verdicts, and the script never guesses between them:
  yes    every rule the profile can decide passes, and no requirement needs a person to read it or says the
         provider selects, reviews or approves. Meeting the rules is not acceptance: the provider still decides
  check  nothing fails, but a requirement needs a person: an invitation, a selection or review by the provider,
         a partner network, a country list, an industry, or a profile field left blank. The requirement is quoted
  no     a rule the profile decides fails: no company for a program that needs one, a later stage, an older company,
         too little funding, no partner code, a nonprofit where the page says for-profit, or none of the profile's
         needs (cpu, gpu, inference, other) among what the program covers
Exit 0: done (or a clean catalog). Exit 1: --check-catalog found a row this script cannot read. Exit 2: a bad
profile, a missing catalog or bad arguments (usage or infrastructure, not a finding).
"""
import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "catalog", "programs.json")

STAGES = ("idea", "pre-seed", "seed", "series-a", "series-b", "series-c", "growth")
PARTNERS = ("none", "vc", "accelerator", "incubator", "angel_network", "university", "community")
BUCKETS = ("no_incorporation", "incorporated", "funded_or_partner")
NEEDS = ("cpu", "gpu", "inference", "other")  # the catalog's covers values
READS = ("id", "program", "provider", "bucket", "credit_max", "covers", "requirements", "max_age_years",
         "funding_rule", "link", "apply_steps", "source", "checked")

# funding_rule values in the catalog, each mapped to its test. A new value upstream fails --check-catalog until it is
# added here, so a rule is never silently treated as "none".
FUNDING_RULES = ("none", "no equity funding allowed", "pre-Series B", "raised over $1M", "recent Series A to E round",
                 "VC from a partner network", "partner or accelerator code", "invite or selection")

# Requirement wording that only a person can judge. Each hit makes the verdict "check" and quotes the line.
# Industry: (pattern, the profile tag that satisfies it).
INDUSTRY = (
    (re.compile(r"generative media", re.I), "generative-media"),
    (re.compile(r"\bweb3\b|blockchain", re.I), "web3"),
    (re.compile(r"\bAI[- ](builder|startup|first|enabled|is core|workloads|applications|development)|voice AI|"
                r"\bAI is core", re.I), "ai"),
)
PLACE = re.compile(r"\bcountr(y|ies)\b|\bbased in\b|\bregistered in\b|\blocated in\b|\bheadquartered\b|"
                   r"\boperations\b.*\bUS\b", re.I)
# The provider selects, reviews or approves: a person decides, so the best a profile earns is "check".
JUDGED = re.compile(r"\b(evaluates?|weighs|decides?|discretion|approv(e|es|ed|al|ing)|select(s|ed|ive|ion)?|"
                    r"review(s|ed|ing)?|case by case|accepted into|sets the amount|invit(e|es|ed|ing|ation))\b",
                    re.I)
# Who decides, when the line names someone other than the provider.
ACCEPTED_INTO = re.compile(r"\baccepted into (.+?)(?:\s*\(|[,;.]|$)", re.I)
NAMED_PARTNER = re.compile(r"\b(?:an? )?((?:approved|select) .+? partner)\b", re.I)
# Lines about the applicant's history, not a judgment: "never approved into the program before".
JUDGED_NOT = re.compile(r"\bnever approved\b|\bpreviously accepted\b", re.I)
FOR_PROFIT_ONLY = re.compile(r"for-profit|not a nonprofit", re.I)
NONPROFIT_OK = re.compile(r"nonprofits? (are )?welcome", re.I)


class Usage(Exception):
    """A bad profile, a missing catalog or bad arguments: exit 2."""


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        raise Usage(f"cannot read the {what} at {path}: {e}")


def validate(p, year):
    """The profile, normalized. Raises Usage with every problem at once. `year` is this year: no future founding."""
    if not isinstance(p, dict):
        raise Usage("the profile must be a JSON object")
    bad = []
    if p.get("stage") is not None and p["stage"] not in STAGES:
        bad.append(f"stage must be one of {', '.join(STAGES)} (or null)")
    f = p.get("funding_usd")
    if f is not None and (isinstance(f, bool) or not isinstance(f, (int, float)) or f < 0):
        bad.append("funding_usd must be a number of US dollars, 0 or more (or null)")
    for key in ("incorporated", "for_profit"):
        if p.get(key) is not None and not isinstance(p[key], bool):
            bad.append(f"{key} must be true, false or null")
    y = p.get("founded_year")
    if y is not None and (isinstance(y, bool) or not isinstance(y, int) or not 1900 <= y <= year):
        bad.append(f"founded_year must be a year from 1900 to {year} (or null)")
    ind = p.get("industry") or []
    if not isinstance(ind, list) or not all(isinstance(t, str) for t in ind):
        bad.append("industry must be a list of tags such as [\"ai\"]")
    loc = p.get("location") or {}
    if not isinstance(loc, dict):
        bad.append("location must be an object such as {\"country\": \"US\", \"region\": \"Colorado\"}")
    needs = p.get("needs") or []
    if not isinstance(needs, list) or not all(n in NEEDS for n in needs):
        bad.append(f"needs must be a list drawn from {', '.join(NEEDS)} (or empty for any)")
    partner = p.get("partner") or {"type": "none"}
    if not isinstance(partner, dict) or partner.get("type", "none") not in PARTNERS:
        bad.append(f"partner.type must be one of {', '.join(PARTNERS)}")
    if bad:
        raise Usage("bad profile: " + "; ".join(bad))
    return dict(p, industry=[t.lower() for t in ind], location=loc, needs=list(needs),
                partner={"type": partner.get("type", "none"), "name": partner.get("name")})


def judge(program, p, year):
    """(verdict, reasons) for one catalog program and one validated profile. Reasons say why, in plain words."""
    fails, checks, notes = [], [], []
    bucket, rule, provider = program["bucket"], program["funding_rule"], program["provider"]

    # What the credits pay for. An empty `needs` means any.
    covers = program.get("covers") or []
    if p["needs"] and not set(p["needs"]) & set(covers):
        fails.append(f"covers {', '.join(covers) or 'nothing stated'}; the profile needs {', '.join(p['needs'])}")

    # A company: the catalog's bucket says "incorporated" needs a registered company (catalog/README.md).
    inc = p.get("incorporated")
    if bucket == "incorporated":
        if inc is False:
            fails.append("needs a registered company; the profile says not incorporated")
        elif inc is None:
            checks.append("needs a registered company; the profile leaves incorporated blank")
    elif bucket == "funded_or_partner" and inc is not True:
        checks.append("the catalog does not say whether this program needs a registered company; "
                      "the profile is not incorporated or leaves it blank")

    # Funding and partner rules.
    stage, raised, ptype = p.get("stage"), p.get("funding_usd"), p["partner"]["type"]
    # The bucket "funded_or_partner" needs outside equity funding, an investor, an accelerator or partner code, or an
    # invitation (catalog/README.md). Its funding_rule may say only the stage ceiling ("pre-Series B"),
    # so the bucket itself is tested here. The partner and invite rules below test it their own way.
    if bucket == "funded_or_partner" and rule not in ("VC from a partner network", "partner or accelerator code",
                                                      "invite or selection"):
        if raised == 0 and ptype == "none":
            fails.append("needs outside equity funding, an investor or a partner code; the profile has raised $0 "
                         "and has no partner")
        elif raised is None and ptype == "none":
            checks.append("needs outside equity funding, an investor or a partner code; the profile leaves "
                          "funding_usd blank")
        else:
            checks.append("needs outside funding or a partner of the kind the requirements name; confirm the "
                          "profile's counts")
    if rule == "none":
        pass
    elif rule == "no equity funding allowed":
        if raised is None:
            checks.append("allows no equity funding; the profile leaves funding_usd blank")
        elif raised > 0:
            fails.append(f"allows no equity funding; the profile has raised ${raised:,.0f}")
    elif rule == "pre-Series B":
        if stage is None:
            checks.append("before Series B only; the profile leaves stage blank")
        elif STAGES.index(stage) >= STAGES.index("series-b"):
            fails.append(f"before Series B only; the profile is at {stage}")
    elif rule == "raised over $1M":
        if raised is None:
            checks.append("needs over $1M raised; the profile leaves funding_usd blank")
        elif raised <= 1_000_000:
            fails.append(f"needs over $1M raised; the profile has raised ${raised:,.0f}")
    elif rule == "recent Series A to E round":
        if stage is None:
            checks.append("needs a recent Series A to E round; the profile leaves stage blank")
        elif STAGES.index(stage) < STAGES.index("series-a"):
            fails.append(f"needs a recent Series A to E round; the profile is at {stage}")
        else:
            checks.append("needs a recent Series A to E round; confirm the round is recent enough")
    elif rule == "VC from a partner network":
        # The catalog names a VC, but the programs' own lines also admit accelerators and incubators (GitHub,
        # Nebius, Anthropic), so only "no partner at all" is decidable.
        if ptype == "none":
            fails.append(f"needs a partner in {provider}'s network (the catalog names a VC); the profile has none")
        else:
            checks.append(f"needs a partner in {provider}'s network (the catalog names a VC); confirm the profile's "
                          f"{ptype.replace('_', ' ')} is in it")
    elif rule == "partner or accelerator code":
        if ptype == "none":
            fails.append(f"needs a code from a partner in {provider}'s network; the profile has no partner")
        else:
            checks.append(f"needs a code from a partner in {provider}'s network; confirm the profile's "
                          f"{ptype.replace('_', ' ')} is one and will issue a code")
    elif rule == "invite or selection":
        checks.append(f"by invitation or selection; {provider} decides")
    else:
        checks.append(f"funding rule this script does not know: {rule!r}; read the requirements")

    # Age: "founded within N years" (catalog/README.md). The boundary year is a check, not a guess.
    limit, founded = program.get("max_age_years"), p.get("founded_year")
    if limit is not None:
        if founded is None:
            checks.append(f"must be founded within {limit} years; the profile leaves founded_year blank")
        else:
            age = year - founded
            if age > limit:
                fails.append(f"must be founded within {limit} years; the profile was founded {age} years ago")
            elif age == limit:
                checks.append(f"must be founded within {limit} years; the profile is at the limit, confirm the date")

    # Requirement wording: the provider's judgment, for-profit, place and industry.
    for line in program.get("requirements") or []:
        if JUDGED.search(line) and not JUDGED_NOT.search(line):
            checks.append(decider(line, provider))
        if FOR_PROFIT_ONLY.search(line) and not NONPROFIT_OK.search(line):
            if p.get("for_profit") is False:
                fails.append(f"for-profit only (\"{line}\"); the profile is a nonprofit")
            elif p.get("for_profit") is None:
                checks.append(f"for-profit only (\"{line}\"); the profile leaves for_profit blank")
        if PLACE.search(line):
            where = ", ".join(v for v in (p["location"].get("region"), p["location"].get("country")) if v)
            checks.append(f"a place rule (\"{line}\"); confirm it fits {where or 'the company'}")
        for pattern, tag in INDUSTRY:
            if pattern.search(line):
                if tag in p["industry"]:
                    notes.append(f"industry rule (\"{line}\") matches the profile's {tag} tag")
                else:
                    checks.append(f"an industry rule (\"{line}\"); the profile has no {tag} tag")
                break

    if fails:
        return "no", fails
    if checks:
        return "check", checks + notes
    return "yes", notes or ["every rule the profile can decide passes"]


def decider(line, provider):
    """The reason for a line where someone decides, naming that someone: another program the startup must be accepted
    into, a partner it must come through, or else the provider."""
    m = ACCEPTED_INTO.search(line)
    if m:
        return f"needs acceptance into {m.group(1).strip()}, which decides (\"{line}\")"
    m = NAMED_PARTNER.search(line)
    if m:
        article = "an" if m.group(1)[0].lower() in "aeiou" else "a"
        return f"needs {article} {m.group(1)}; confirm the profile has one (\"{line}\")"
    return f"{provider} decides (\"{line}\")"


def match(catalog, profile, year):
    p = validate(profile, year)
    out = []
    for prog in catalog["rows"]:
        verdict, reasons = judge(prog, p, year)
        out.append({"id": prog["id"], "program": prog["program"], "provider": prog["provider"],
                    "credit_max": prog.get("credit_max"), "verdict": verdict, "reasons": reasons,
                    "requirements": prog.get("requirements") or [], "apply_link": prog.get("link"),
                    "apply_steps": prog.get("apply_steps") or [], "source": prog["source"],
                    "checked": prog["checked"]})
    rank = {"yes": 0, "check": 1, "no": 2}
    out.sort(key=lambda r: (rank[r["verdict"]], -(r["credit_max"] or 0), r["provider"].lower()))
    return out


def report(results, catalog_checked):
    """The short list: programs to apply for (yes), then ones to confirm (check), each with its steps and link.
    Programs that do not qualify are named on one line each, with the first reason."""
    lines = [f"Programs from the catalog checked {catalog_checked}. Amounts are the published ceilings, as each "
             "source page states them. Meeting the rules is not acceptance: each provider decides.", ""]
    titles = {"yes": "Apply: you meet every stated rule", "check": "Confirm first, then apply"}
    for verdict in ("yes", "check"):
        group = [r for r in results if r["verdict"] == verdict]
        lines.append(f"## {titles[verdict]} ({len(group)})")
        for r in group:
            amount = f"up to ${r['credit_max']:,}" if r["credit_max"] else "amount not stated"
            lines.append(f"- {r['provider']}: {r['program']} ({amount})")
            if verdict == "check":
                for why in r["reasons"]:
                    lines.append(f"    confirm: {why}")
            for n, step in enumerate(r["apply_steps"], 1):
                lines.append(f"    {n}. {step}")
            lines.append(f"    apply: {r['apply_link']}")
            lines.append(f"    source: {r['source']} (read {r['checked']})")
        lines.append("")
    group = [r for r in results if r["verdict"] == "no"]
    lines.append(f"## Not a match ({len(group)})")
    lines += [f"- {r['provider']}: {r['program']}: {r['reasons'][0]}" for r in group]
    return "\n".join(lines) + "\n"


def check_catalog(catalog):
    """Findings: rows missing a field this script reads, an unknown bucket, cover or funding rule, or no steps."""
    out = []
    for r in catalog.get("rows") or []:
        name = r.get("id", "?")
        missing = [k for k in READS if k not in r]
        if missing:
            out.append(f"{name}: missing {missing}")
        if r.get("bucket") not in BUCKETS:
            out.append(f"{name}: bucket {r.get('bucket')!r} is not one this script knows")
        if r.get("funding_rule") not in FUNDING_RULES:
            out.append(f"{name}: funding_rule {r.get('funding_rule')!r} is not in FUNDING_RULES; add its test")
        if r.get("max_age_years") is not None and not isinstance(r["max_age_years"], int):
            out.append(f"{name}: max_age_years is not a whole number")
        if not set(r.get("covers") or []) <= set(NEEDS):
            out.append(f"{name}: covers {r.get('covers')!r} has a value not in NEEDS")
        if not r.get("apply_steps") or not r.get("link"):
            out.append(f"{name}: no apply_steps or no link, so the short list cannot say how to apply")
    if not catalog.get("rows"):
        out.append("the catalog has no rows")
    return out


def self_test():
    year = 2026

    def prog(pid, bucket="incorporated", rule="none", age=None, reqs=(), covers=("gpu",)):
        return {"id": pid, "program": pid, "provider": "Prov", "bucket": bucket, "credit_max": 1000,
                "covers": list(covers), "requirements": list(reqs), "max_age_years": age, "funding_rule": rule,
                "link": "https://example.com/apply", "apply_steps": ["Read the page.", "Apply."],
                "source": "https://example.com", "checked": "2026-11-02"}

    catalog = {"rows": [
        prog("open", bucket="no_incorporation"),
        prog("company"),
        prog("young", age=5),
        prog("pre-b", rule="pre-Series B", age=10),
        prog("for-profit", reqs=["Privately held and for-profit"]),
        prog("nonprofit-ok", reqs=["Registered in the US as a corporation, LLC or LP (nonprofits welcome)"]),
        prog("ai-only", reqs=["AI is core to the primary product"]),
        prog("place", reqs=["Headquartered in a country where Azure is available"]),
        prog("vc-network", bucket="funded_or_partner", rule="VC from a partner network"),
        prog("code", bucket="funded_or_partner", rule="partner or accelerator code"),
        prog("invite", bucket="funded_or_partner", rule="invite or selection"),
        prog("raised-1m", bucket="funded_or_partner", rule="raised over $1M"),
        prog("series", bucket="funded_or_partner", rule="recent Series A to E round"),
        prog("funded-pre-b", bucket="funded_or_partner", rule="pre-Series B"),
        prog("no-equity", rule="no equity funding allowed"),
        prog("mystery", rule="a rule nobody wrote down"),
        prog("selective", reqs=["Selective: the provider cannot accept every applicant"]),
        prog("history", reqs=["First-time applicant (never approved into the program before)"]),
        prog("invites", reqs=["Apply; the provider invites a select group of builders"]),
        prog("reviews", reqs=["We review every application before approving it"]),
        prog("select-partner", reqs=["Affiliation with a select Notion startup partner for the 6-month offer"]),
        prog("accepted-into", reqs=["Accepted into NVIDIA Inception (so incorporated)"]),
        prog("approved-partner", reqs=["Raised at least $5M from an approved Nebius VC partner"]),
        prog("cpu-only", bucket="no_incorporation", covers=("cpu", "other")),
    ]}
    good = {"stage": "pre-seed", "funding_usd": 0, "incorporated": True, "for_profit": True, "founded_year": 2025,
            "industry": ["ai"], "location": {"country": "US", "region": "Colorado"}, "partner": {"type": "none"}}
    bad = {"stage": "series-c", "funding_usd": 900000, "incorporated": False, "for_profit": False,
           "founded_year": 2006, "industry": [], "location": {"country": "US"}, "partner": {"type": "none"}}
    blank = {}
    with_vc = dict(good, stage="series-a", funding_usd=2_000_000, partner={"type": "vc", "name": "A Fund"})
    with_accelerator = dict(good, stage="seed", funding_usd=500_000, partner={"type": "accelerator", "name": "A"})
    gpu = dict(good, needs=["gpu"])
    want = {  # profile -> program -> verdict
        "good": {"open": "yes", "company": "yes", "young": "yes", "pre-b": "yes", "for-profit": "yes",
                 "nonprofit-ok": "check", "ai-only": "yes", "place": "check", "vc-network": "no", "code": "no",
                 "invite": "check", "raised-1m": "no", "series": "no", "no-equity": "yes", "mystery": "check",
                 "funded-pre-b": "no", "selective": "check", "history": "yes", "invites": "check",
                 "reviews": "check", "select-partner": "check", "accepted-into": "check", "approved-partner": "check",
                 "cpu-only": "yes"},
        "bad": {"open": "yes", "company": "no", "young": "no", "pre-b": "no", "for-profit": "no",
                "nonprofit-ok": "no", "ai-only": "no", "place": "no", "vc-network": "no", "code": "no",
                "invite": "check", "raised-1m": "no", "series": "check", "no-equity": "no", "mystery": "no",
                "funded-pre-b": "no"},
        "blank": {"open": "yes", "company": "check", "young": "check", "pre-b": "check", "for-profit": "check",
                  "code": "no", "raised-1m": "check", "no-equity": "check", "funded-pre-b": "check"},
        "with_vc": {"vc-network": "check", "code": "check", "raised-1m": "check", "series": "check",
                    "pre-b": "yes", "no-equity": "no", "funded-pre-b": "check"},
        "with_accelerator": {"vc-network": "check", "code": "check", "funded-pre-b": "check"},
        "gpu": {"open": "yes", "cpu-only": "no"},
    }
    profiles = {"good": good, "bad": bad, "blank": blank, "with_vc": with_vc, "with_accelerator": with_accelerator,
                "gpu": gpu}
    cases = []
    for pname, expect in want.items():
        got = {r["id"]: r for r in match(catalog, profiles[pname], year)}
        for pid, verdict in expect.items():
            ok = got[pid]["verdict"] == verdict
            cases.append((f"{pname} profile, {pid}: {verdict}" + ("" if ok else f" (got {got[pid]['verdict']})"), ok))
    got = {r["id"]: r for r in match(catalog, good, year)}
    cases.append(("acceptance into another program names that program, not the provider",
                  any("NVIDIA Inception, which decides" in w for w in got["accepted-into"]["reasons"])
                  and not any("Prov decides" in w for w in got["accepted-into"]["reasons"])))
    cases.append(("an approved or select partner names that partner",
                  any("approved Nebius VC partner" in w for w in got["approved-partner"]["reasons"])
                  and any("needs a select Notion startup partner" in w for w in got["select-partner"]["reasons"])))
    cases.append(("every result carries the apply link and steps",
                  all(r["apply_link"] and r["apply_steps"] for r in got.values())))
    text = report(match(catalog, gpu, year), "2026-11-02")
    cases.append(("the short list prints numbered steps and the apply link",
                  "    1. Read the page." in text and "apply: https://example.com/apply" in text))
    cases.append(("the short list names a non-match on one line with its reason",
                  "- Prov: cpu-only: covers cpu, other; the profile needs gpu" in text))
    # Every non-yes verdict says why; every result cites its source.
    allr = match(catalog, bad, year)
    cases.append(("every result carries reasons and a source", all(r["reasons"] and r["source"] for r in allr)))
    cases.append(("a 'no' quotes the requirement it failed",
                  any('"Privately held and for-profit"' in w for r in allr if r["id"] == "for-profit"
                      for w in r["reasons"])))
    # Bad profiles are refused, not guessed.
    for name, prof in (("an unknown stage", {"stage": "series-z"}), ("a string amount", {"funding_usd": "1M"}),
                       ("an unknown partner type", {"partner": {"type": "friend"}}),
                       ("a yes/no field given as text", {"incorporated": "yes"}),
                       ("a founding year in the future", {"founded_year": year + 1}),
                       ("a founding year before 1900", {"founded_year": 1899}),
                       ("an unknown need", {"needs": ["quantum"]}), ("needs given as text", {"needs": "gpu"})):
        try:
            match(catalog, prof, year)
            cases.append((f"{name} is refused (exit 2)", False))
        except Usage:
            cases.append((f"{name} is refused (exit 2)", True))
    # The catalog check catches what this script cannot read.
    findings = check_catalog(catalog)
    cases.append(("--check-catalog flags an unknown funding rule", any("mystery" in f for f in findings)))
    cases.append(("--check-catalog passes the known rows",
                  len(findings) == 1
                  and check_catalog({"rows": [r for r in catalog["rows"] if r["id"] != "mystery"]}) == []))
    cases.append(("--check-catalog flags a missing field",
                  any("missing" in f for f in check_catalog({"rows": [{"id": "x", "bucket": "incorporated"}]}))))
    cases.append(("--check-catalog flags a row with no apply steps",
                  any("no apply_steps" in f for f in check_catalog({"rows": [dict(prog("x"), apply_steps=[])]}))))
    cases.append(("--check-catalog flags an unknown cover",
                  any("covers" in f for f in check_catalog({"rows": [dict(prog("x"), covers=["tpu"])]}))))

    for name, ok in cases:
        print(f"self-test: {'ok   ' if ok else 'WRONG'} {name}")
    wrong = sum(1 for _, ok in cases if not ok)
    print(f"self-test: {len(cases) - wrong} of {len(cases)} cases behave")
    return 1 if wrong else 0


def main(argv):
    args = argv[1:]
    try:
        if args == ["--self-test"]:
            return self_test()
        if args == ["--check-catalog"]:
            out = check_catalog(load_json(CATALOG, "catalog"))
            for line in out:
                print(f"match: {line}")
            print("match: the catalog is readable" if not out else f"match: {len(out)} finding(s)")
            return 1 if out else 0
        if len(args) in (1, 2) and not args[0].startswith("--") and args[1:] in ([], ["--json"]):
            catalog = load_json(CATALOG, "catalog")
            results = match(catalog, load_json(args[0], "profile"), datetime.date.today().year)
            print(json.dumps(results, indent=2) if args[1:] else report(results, catalog.get("checked")), end="")
            if args[1:]:
                print()
            return 0
        print(__doc__.split("\n\n")[1])
        return 2
    except Usage as e:
        print(f"match: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
