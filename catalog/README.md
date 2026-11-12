# catalog

`programs.json` is the one source of startup credit program facts for Colorado Startups. Other repositories copy it from here. A fix lands here by pull request, never in a copy.

| File | What it is |
|---|---|
| `programs.json` | The programs, one row each, in canonical layout (sorted by bucket, provider, then program) |
| `check.py` | Guards the file: exact fields, plain text, https links, dates, steps, no private fields |

## A row

| Field | Holds |
|---|---|
| `id` | A slug, unique |
| `program`, `provider` | The names the provider's page uses |
| `bucket` | `no_incorporation` (anyone), `incorporated` (needs a registered company) or `funded_or_partner` (needs outside funding, an investor or accelerator code, or an invitation) |
| `credit_first`, `credit_max` | US dollars at sign-up and at most, or `null` when the page states none. A `_computed` flag is `true` when the number is added up here, and then `amount_note` says "(computed here)" |
| `amount_note` | The amount in the page's terms |
| `covers` | What the credits pay for: `cpu`, `gpu`, `inference`, `other` |
| `requirements` | Who qualifies, one line each, in the page's terms |
| `max_age_years` | "Founded within N years", or `null` |
| `funding_rule` | One of the rules `match/match.py` tests, such as `none`, `pre-Series B` or `invite or selection` |
| `term` | How long the credits last |
| `traps` | `card_required`, `expiry`, `overage` (`bills`, `stops` or `unknown`), `trains_on_data` and `other` notes |
| `link` | The first-party page where the application or sign-up starts |
| `apply_steps` | 2 to 5 steps a founder takes, each under 25 words |
| `source`, `checked` | The page read, and the date it was read |

## What stays out

A program is left out when its page says it is closed, when its page cannot be read, when the page does not confirm the program or its amount, or by Colorado Startups policy. Application drafts, partner tracks, account records and any `cs_*` or `evidence` field stay in a private repository. `check.py` and `tools/checks.py` refuse them here.

## Commands

| Command | What it does |
|---|---|
| `python3 -I catalog/check.py` | Every row passes; exit 1 names each finding |
| `python3 -I catalog/check.py --fix` | Rewrites the file in canonical layout, then checks it |
| `python3 -I catalog/check.py --self-test` | Seeded good and bad catalogs that must pass or fail |
| `python3 -I match/match.py --check-catalog` | Every row has what the matcher reads |
