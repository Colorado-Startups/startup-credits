# Startup credits

Find your credits, then apply.

This repository lists 45 free startup credit programs for compute, GPUs, inference and software. Each program shows who qualifies, the amount, a first-party apply link and the steps. Every row was read on the provider's own page on its `checked` date. A program closes or changes without notice, so read its source page before you apply.

Credits anyone can get, with no company needed (cloud trials and free tiers), are in [Colorado-Compute/compute-credits](https://github.com/Colorado-Compute/compute-credits).

| Step | Do this |
|---|---|
| 1. Describe your startup | Copy [`match/examples/colorado-preseed-ai.json`](match/examples/colorado-preseed-ai.json) and set your stage, funding, company and needs. Leave a field `null` when you do not know it |
| 2. Get your short list | `python3 -I match/match.py my-startup.json` (Python 3, no installs) |
| 3. Apply | Work down the list. Each program prints its steps, its apply link and the page it was read on |

No Python? Read [the founder guide](guides/free-gpu-credits-for-founders.md), or open [`catalog/programs.json`](catalog/programs.json) and filter by `bucket`.

## What is here

| Path | What it is |
|---|---|
| [`catalog/`](catalog/README.md) | `programs.json`, the 45 programs, and `check.py`, which guards every field |
| [`match/`](match/README.md) | The matcher: your profile in, a short list out, each program with its apply steps |
| [`guides/`](guides/free-gpu-credits-for-founders.md) | The founder guide: which programs to apply for first, and how to avoid a surprise bill |
| [`program/DESIGN.md`](program/DESIGN.md) | The design of the Colorado Startups Accelerator Program, a free, non-equity cohort (not running yet) |
| `tools/` | The repository's text checks and its secret scan |

## The two buckets

| Bucket | Means | Programs |
|---|---|---|
| `incorporated` | Needs a registered company | 27 |
| `funded_or_partner` | Needs outside funding, an investor or accelerator code, or an invitation | 18 |

Counts are from `catalog/programs.json`, checked 2026-11-12.

## Fix a program

Open a pull request that edits `catalog/programs.json`. Update the row's `source` and `checked` to the page you read today. Run `python3 -I catalog/check.py --fix` to write the canonical layout, then `python3 -I catalog/check.py`. CI runs every check on the pull request. Sign off each commit with `git commit -s`.

Colorado Startups publishes this list for founders; it is not a partner of any provider listed, and no provider paid to appear.

## License

Everything Colorado Startups wrote here is dedicated to the public domain under [CC0 1.0](LICENSE). Use it for anything, with no credit needed. The code (`tools/`, `match/match.py`, `catalog/check.py`, `.github/workflows/`) is also offered under [0BSD](LICENSES/0BSD.txt), whichever you prefer. Your contribution comes in under the same terms. Provider names and marks belong to their owners.
