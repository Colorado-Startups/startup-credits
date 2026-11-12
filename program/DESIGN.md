# Colorado Startups Accelerator Program: design

Status: design, not running. Nothing here is live until the public page at `coloradostartups.org/accelerator/` ships. Numbers marked "proposed" are goals, not counts.

## Two layers

| Layer | Who | How you join | What it is |
|---|---|---|---|
| The community | Everyone building in Colorado, and the people who back them | Ask to join the Slack or the LinkedIn Group | Anyone may ask to join; a person approves each new member (coloradostartups.org/community/, read 2026-11-03) |
| The Accelerator Program | Colorado companies in energy, compute or open-weight models that pass the threshold | Apply; a panel selects | A free, non-equity cohort with structured support and help with credit programs |

## The program in one table

| | Design |
|---|---|
| Focus | Energy, compute and open-weight models |
| What it is | A free, non-equity accelerator: a published threshold, a quarterly cohort, office hours, expert sessions and a showcase |
| Price | Free. No equity, no fee, no revenue share |
| Who runs it | Colorado Startups, Ltd. (Denver), the legal entity on every coloradostartups.org page footer (read 2026-11-03) |
| Applications | Rolling, reviewed into a quarterly cohort |
| Cohort size | Up to 10 companies (proposed) |
| Cohort term | 12 weeks of structured support; members stay in the alumni channel after |

Colorado Startups does not invest, and it is no provider's partner until that provider accepts it.

## The threshold

A company joins the cohort once it meets every row. Each rule names the credit program rule it lines up with, so every member can apply to those programs. Rows cite `catalog/programs.json` by id.

| # | Rule | Lines up with |
|---|---|---|
| 1 | Headquartered in Colorado, or most of the full-time team lives in Colorado | Microsoft: "Headquartered in a country where Azure is available" (`microsoft`) |
| 2 | A registered legal entity, with name and address matching its formation documents | NVIDIA Inception: "Officially incorporated" (`inception`); Microsoft Investor Network: name and address match the company's legal documents (`microsoft-investor-network`) |
| 3 | For-profit and privately held | Microsoft: "Privately held and for-profit" (`microsoft`) |
| 4 | Builds in energy, compute or open-weight models | NVIDIA: a clear use case for NVIDIA technology (`inception`) |
| 5 | Has a working product, a pilot, or a public model or dataset release | Microsoft: a software product or service the company owns (`microsoft`) |
| 6 | One traction signal: a paying customer, a signed pilot, a non-dilutive grant, or 1,000 downloads of an open-weight release in its first 90 days (proposed) | None; it is ours |
| 7 | Not raised Series C or later | Microsoft: "Not raised Series C or later" (`microsoft`) |
| 8 | Founded within the last 10 years | NVIDIA Inception and AWS Activate age limits (`inception`, `aws-activate-portfolio`) |
| 9 | Not a consultancy, agency, reseller or crypto company | Microsoft and NVIDIA exclusions (`microsoft`, `inception`) |

## The application

Rolling, about 10 minutes (proposed). Responses live in Colorado Startups' private storage, never in git.

| # | Question | Threshold row |
|---|---|---|
| 1 | Founder name and contact | n/a |
| 2 | Company name and website | 2, 5 |
| 3 | Where is the company headquartered, and where does the team live? | 1 |
| 4 | Registered entity: state, type, formation date | 2, 8 |
| 5 | For-profit and privately held? | 3 |
| 6 | Which focus: energy, compute or open-weight models? What do you build? (3 sentences) | 4 |
| 7 | Link to the product, pilot, or model or dataset release | 5 |
| 8 | Your traction signal, with evidence | 6 |
| 9 | Stage and outside equity raised, in bands (none, under $500,000, $500,000 to $2M, over $2M) | 7 |
| 10 | Which credits would you use in the next 6 months, and for what? | n/a |
| 11 | Credits already received from each provider | n/a |
| 12 | Other programs you are in (accelerators, investors) | n/a |
| 13 | Consent to share your company name, website and contact with a provider that issues you a code | Codes |

## Selection

| Step | Design |
|---|---|
| Threshold check | A person, or an AI agent disclosed as one, checks rows 1 to 9 against the evidence. AI never scores or decides |
| Panel | The program lead plus two volunteer reviewers from the community |
| Conflicts | A reviewer with a stake in an applicant (employee, investor, family, advisor) leaves that application |
| Rubric | Four scores, 1 to 5 each: the traction signal; fit with energy, compute or open weights; a real plan to use the credits within 6 months; the founder's part in the community. Total out of 20 |
| Decision | Companies that pass the threshold, by score, up to the cohort size, by majority of the panel |
| Waitlist | A company that passes but misses the cut rolls into the next quarter's review |
| Reply | Every applicant hears back within 14 days of the quarter's review (proposed) |

## Cadence

| Week of the quarter | What happens |
|---|---|
| Any | Applications arrive; the threshold check runs within 14 days (proposed) |
| 1 to 2 | Panel review of every application that passed since the last review |
| 3 | Replies; the cohort announced in the Slack, with each company's yes |
| 4 to 15 | 12 weeks: office hours every other week, one expert session a month |
| 15 | Showcase; each company reports what it used (one question) |

## What cohort members get

| Item | Condition |
|---|---|
| Help applying to the direct programs in `catalog/programs.json`, starting from `match/match.py` | Each startup applies itself |
| Office hours, every other week for 12 weeks (60 minutes, group) | Starts with cohort 1 |
| Expert sessions, monthly: power and grid interconnection, GPU and compute procurement, open-weight licensing | Hosts from the community |
| A cohort channel, then an alumni channel, in the Colorado Startups Slack | The Slack exists (coloradostartups.org/community/, read 2026-11-03) |
| A showcase at the end of the term (virtual) | Starts with cohort 1 |
| Provider credit codes | Only from providers that accept Colorado Startups as a partner, and only in the words their terms allow |

## How codes are issued

1. A provider accepts Colorado Startups and gives access to its portal or a batch of codes.
2. One named program lead holds the portal login. No file in this repository ever holds a code.
3. For each selected company, the lead sends one code to that founder only. Never in a Slack channel, a group message or git.
4. The lead records "code sent, date, provider" in private storage, never the code itself.
