# match

Your startup's profile in, a short list of credit programs out. Each program on the list prints its apply steps, its first-party apply link and the page its facts were read on. Python 3, standard library only.

```bash
python3 -I match/match.py match/examples/colorado-preseed-ai.json
```

Add `--json` for machine-readable output.

## The profile

Leave a field `null` when you do not know it. The matcher then says "confirm" instead of guessing.

| Field | Values | Used for |
|---|---|---|
| `stage` | `idea`, `pre-seed`, `seed`, `series-a`, `series-b`, `series-c`, `growth` | Stage ceilings ("pre-Series B") and floors ("Series A to E") |
| `funding_usd` | Outside equity raised so far, in US dollars (0 for none) | "Raised over $1M", "no equity funding", and programs that need funding |
| `incorporated` | `true` or `false` | Programs that need a registered company |
| `for_profit` | `true` or `false` | Requirements that say "for-profit" or "not a nonprofit" |
| `founded_year` | A year, such as `2025` | "Founded within N years" |
| `industry` | Tags: `ai`, `generative-media`, `web3` | Requirements that name an industry |
| `needs` | Any of `cpu`, `gpu`, `inference`, `other`; empty for any | Drops programs whose credits cover none of them |
| `location` | `{"country": "US", "region": "Colorado"}` | Shown when a requirement names a place |
| `partner` | `{"type": "none" \| "vc" \| "accelerator" \| "incubator" \| "angel_network" \| "university" \| "community", "name": ...}` | Programs that need a partner code or a VC in a network |

## The short list

| Section | Verdict | Means |
|---|---|---|
| Apply | `yes` | Every rule the profile decides passes, and no requirement says the provider selects, reviews or approves. It is not acceptance: the provider still decides |
| Confirm first, then apply | `check` | Nothing fails, but a quoted requirement needs a person: an invitation, a review, a partner network, a country list, an industry, or a blank profile field |
| Not a match | `no` | A rule the profile decides fails. One line names it |

When the profile's `incorporated` is `false` or blank, the short list opens with a pointer to [Colorado-Compute/compute-credits](https://github.com/Colorado-Compute/compute-credits), where credits that need no company live.

The matcher reads `bucket`, `funding_rule`, `max_age_years` and `covers` as rules. It reads `requirements` text only to flag lines for a person. It never turns free text into a "no", with one exception: "for-profit" or "not a nonprofit" against a profile that says `for_profit: false`.

## Checks

| Command | What it proves |
|---|---|
| `python3 -I match/match.py --self-test` | Seeded profiles and programs that must match, need a check or fail; bad profiles refused; the short list prints steps and links |
| `python3 -I match/match.py --check-catalog` | Every catalog row has the fields the matcher reads, a known `funding_rule` and `covers`, and apply steps with a link |

A new `funding_rule` fails `--check-catalog` until `FUNDING_RULES` and `judge()` handle it. Until then the matcher answers "confirm" for that program, never "apply".

## Examples

`examples/` holds made-up profiles, never a real company's data.
