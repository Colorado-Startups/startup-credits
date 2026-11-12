# Free GPU and cloud credits for founders

November 12, 2026. Every amount and rule below comes from the provider's own page, read on November 12, 2026. Each row names its id in [`catalog/programs.json`](../catalog/programs.json), which holds the source link. A program can change or close without notice, so read its page before you apply.

## The short version

| Order | Program | Amount, per the provider's page | Needs | id |
|---|---|---|---|---|
| 1 | NVIDIA Inception | No cash; members request partner benefits in a portal | A registered company under 10 years old | `inception` |
| 2 | Lambda for Inception members | $1,000 of GPU credit for 12 months | Inception membership and a card | `lambda` |
| 3 | Microsoft for Startups | $200 at sign-up, $5,000 after business verification, up to $150,000 at usage milestones | A new personal Microsoft account; not past Series B | `microsoft` |
| 4 | Runpod Startup Program, Starter | $1,000, expiring 1 year after issue | Under $1M raised | `runpod-startup` |
| 5 | Cloudflare for Startups, Tier 3 | $10,000 for 12 months | Under $1M raised and a company email domain | `cloudflare-tier3` |
| 6 | AWS Activate | $1,000, with up to $5,000 for select participants | A Paid Tier AWS account; not past Series A | `aws-activate` |

The catalog lists 45 programs. Run [`match/match.py`](../match/README.md) with your own profile for the full short list.

## Before you apply

| Do this | Why, per the provider's page |
|---|---|
| Use an email on your company's domain | AWS Activate, Cloudflare and Baseten refuse free email providers |
| Open a new Microsoft account for Microsoft for Startups | Microsoft for Startups needs a new personal Microsoft account with no prior Azure offer, so an Azure free account login does not qualify (`microsoft`) |
| Apply for Kiro before AWS Activate if you want both | Kiro startup credits exclude startups with active Activate Credits (`aws-activate`) |
| Know that the AWS Free plan blocks Activate | A Free plan account is not eligible for promotional credits; a Paid plan account is (`aws-free-plan` in compute-credits) |
| Skip the Baseten $250 credit if you want the startup program | The Baseten AI Startup Program only enrolls net new customers that never received Baseten credits (`baseten-startup`) |
| Activate Microsoft credits in time | Microsoft says credits must be activated within 90 days of accepting the agreement, with no extensions (`microsoft`) |

## No company yet

Credits anyone can get with no company, such as the AWS Free plan, the Azure free account, the Oracle Cloud Free Trial, AMD Developer Cloud, Modal Starter and Deepgram, are in [Colorado-Compute/compute-credits](https://github.com/Colorado-Compute/compute-credits). Each row there has its amount, its card rule and what happens past the credit.

## Once you are incorporated

| Program | Amount | Watch for | id |
|---|---|---|---|
| Akamai Rise | $500 to $120,000 in the first year | A credit card and a company domain email | `akamai-rise` |
| Denvr AI Ascend | $1,000 to $25,000 to start, plus up to $500,000 in reward credits earned from spend | Denvr picks by fit | `denvr-ascend` |
| OVHcloud Startup Program | Up to $12,000 for 12 months (US program) | Pre-seed or seed, selected | `ovhcloud` |
| ElevenLabs Grants | 12 months of the Scale plan, which ElevenLabs values at $5,500 | Fewer than 25 employees | `elevenlabs` |
| fal Startup Program | $1,000 to start | Teams in Europe or Asia only | `fal-startup` |
| Vast.ai Startup Program | A dollar-for-dollar match on paid spend | No upfront credit | `vast` |

## Needs funding or a partner

These ask for outside funding, a partner investor or an invitation, per each provider's page.

| Program | Amount | Needs | id |
|---|---|---|---|
| Runpod Startup Program, Venture | $5,000 | A verified VC portfolio company under $5M raised | `runpod-startup` |
| Cloudflare for Startups, Tiers 2 and 1 | $100,000 or $350,000 | A Cloudflare affiliated partner investor | `cloudflare-tier2-1` |
| Together AI Startup Accelerator | Up to $15K on the Build tier | Selection; up to $5M raised | `together` |
| Anthropic startup credits | Up to $100,000 | A partner VC | `new-anthropic-vc-credits` |
| GitHub for Startups | $10,000 of GitHub credit | A GitHub for Startups partner | `github-startups` |
| Koyeb Startup Program | Up to $30k | A partner accelerator, or $1M to $5M from VCs | `koyeb-startup` |

## Protect yourself from a surprise bill

Most programs put a card on file and bill you once the credit runs out. The catalog marks each one in `traps.overage`.

| Provider | What stops the spend, per its own docs (read 2026-11-12) |
|---|---|
| [AWS](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/budgets-controls.html) | AWS Budgets actions can apply an IAM policy or a service control policy, or target specific EC2 or RDS instances, when a budget is crossed. They run automatically or after your approval |
| [Azure](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit) | Free accounts have the spending limit on by default. At the limit, Azure disables your services for the rest of the billing period. You remove the limit only by upgrading to pay as you go |
| Cloudflare | After the credits expire, Cloudflare bills the card on file |

Set a budget alert on day one with every provider that holds your card.

## Questions

Ask in the Colorado Startups community: [coloradostartups.org/community/](https://coloradostartups.org/community/). To fix a program, open a pull request on [`catalog/programs.json`](../catalog/programs.json).
