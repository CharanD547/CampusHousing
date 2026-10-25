# Rubric-driven improvements — October 25, 2026

## Completed

- Read all 19 pages of the supplied updated event PDF and visually inspected submission/scoring pages 12, 14 and 15. The rubric allocates 25 points each to impact, technical/AI architecture, responsible AI/accessibility and feasibility/sustainability.
- Added a property-specific quote/fee gap service and `/api/v1/research/lease-gaps`. All 44 priced properties need a current written quote; the three directory-only references need additional price evidence. The full checklist is in [FEES_AND_LEASE_QUOTES.md](FEES_AND_LEASE_QUOTES.md).
- Added the **Before you commit** panel, a copy-only quote request and exact-plan assistant context. The assistant handoff preserves the user's shortlist and does not automatically call a model or send a landlord a message.
- Corrected an AI context bug that classified every guide-linked operator offer as guide-only. Sourced asking figures are now distinguished from unsourced guide numbers.
- Bounded source snippets/history; checked candidate-specific citations and monetary claims across all output fields. Added a pre-inference refusal for discriminatory ranking and targeted guards for observed unsupported certainty and mixed-language fragments. Local fallback now includes unresolved comparison notes and preserves property facts when the question mentions both price and billing.
- Restored a shared persistent Google Places/Routes attempt budget, capped at the user's authorized 60 per UTC day (configurable lower); failures count. Browser SDK use still requires separate provider quotas.
- Packaged the exact historical 240 authored synthetic examples, hashes, training reports and all available generation evaluations for Git. Preserved the historical manifest-label discrepancy and weaker v3 results. No reviews, chats, weights or workspaces were copied.
- Added a model card, reproducibility notes, two-minute demo script, impact-validation task and criterion-by-criterion readiness matrix. Refreshed OpenAPI and the relevant README/configuration documentation.

## Actual verification

- **100 Python tests and 26 Node tests passed.** One existing Starlette/httpx deprecation warning remains.
- A separate backend with fresh temporary SQLite passed the production HTTP release flow, including the new gap endpoint, 304 offers, 44 priced properties and 47 gap records. This test made zero live paid provider calls.
- The historical dataset's split hashes and 192/24/24 counts match the copied training reports. Training preflight ran without training, downloading weights or changing the existing adapter.
- Six independent application cases were run through the actual local Gemma-backed API twice. Initial answers exposed issues; after targeted guards the repeat returned three model answers, two explicit fallbacks and one pre-inference policy refusal. Both response sets and limitations are under `data/evaluation/`. These are authored agent-reviewed checks, not human-reviewed accuracy measurements.
- Visible Chrome tested all 44 property pages for quote/assistant controls, invalid layout and overflow. The quote textarea, keyboard focus, copy operation and exact-plan assistant context were checked. The clipboard matched the displayed request after asynchronous write completion. The shortlist remained unchanged.
- The quote panel also fit a 390-pixel phone viewport. Browser screenshots are under `var/rubric-review-20261025/browser/`.
- Additional live browser assistant testing showed an explicit validated-output fallback and a busy response retaining the question. Do not claim every model question succeeds. The single-request guard and honest provider labels remain visible.
- Main SQLite databases were backed up before this work. Existing uncommitted work, private records and frozen briefs were preserved. No commit, push, deployment, operator message or platform submission was performed.

## Still requires a person or external evidence

- A real two-minute demo recording, submission to both required platforms and verification of receipts.
- One consenting student usability session or other real stakeholder validation; no fabricated testimony, savings or adoption claims.
- Current written operator quotes and complete fee schedules. Maple Ridge has no structured fee amounts; Smith's Landing and Union have listed charges with missing amounts; Edge, Brexx and Union lack installment counts; 37 properties lack exact start/end dates.
- Improved model generalization and a human-reviewed held-out evaluation. Existing shared-template scores do not measure factual accuracy.
- A verified public hosting path if desired. Docker CLI is absent here, so the container recipe was not executed. The current GPU recipe is not a demonstrated low-memory deployment.
- Commit/push the tested source/data/docs. The actual weights/adapters remain local and excluded from Git.

## Publication follow-up

The initial audit above packaged data/reports only. The subsequent authorized publication also includes the second historical synthetic dataset, all three training reports, and the actual v1/v2/v3 learned LoRA adapters under `models/`, with hashes, portable configs, Apache-2.0 license and notices. v2 remains selected; v3 regression and its local-base revision limitation are documented. Base weights and private runtime data remain excluded.
