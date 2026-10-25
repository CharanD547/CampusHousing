# Roomwise housing and Gemma review

Reviewed October 24, 2026, evening EDT. The main app is available at `http://127.0.0.1:8001/` and remains bound to `0.0.0.0` with the existing local/LAN authentication rules.

## Git and preservation

`git fetch origin --prune` succeeded before implementation. Local `main` and `origin/main` both resolved to `306cb73a3db0860d077b957328c76fee5a7bc8a6`. No upstream commits were missing. The pre-existing edits to the training documentation, trainer and assistant tests were retained and extended. This review does not create or push a commit.

Before replacing catalog rows, all seven SQLite databases were backed up to `var/backups/pre-guide-review-20261024/`, with integrity checks and SHA256 manifest. Old catalog/source versions are archived in the catalog database; immutable comparisons and briefs are not rewritten. Credentials and model weights are excluded from backups and Git. A scan of all tracked and eligible untracked files found no configured secret values.

## Main findings and fixes

| Finding | Result |
|---|---|
| Checked-in seed had 68 plans but running database retained 18 original rows | Added explicit preview/apply catalog sync, archived replaced versions, applied all 68 plans to the running database |
| A new fee source made old rent appear fresh | Freshness now follows the offer's price source, with a regression test |
| UTC timestamps after midnight displayed as tomorrow in Blacksburg | Frontend review dates now use America/New_York |
| Property ranges could display missing prices as infinity/zero | Unknown price and billing basis render explicitly; one property card contains its plan list/ranges |
| More than one plan from the same place could occupy the shortlist | Selecting a new plan for an already-shortlisted property replaces that property's selected plan |
| Terrace widget explicitly states monthly frequency | Catalog retains calendar-month frequency for its displayed leasing totals, separate from Alight/Union/Mill installments |
| Public asking figures were labeled portal quotes, and undated leases labeled 2027–28 | Published asking-price tiers and unconfirmed lease dates now stay explicit |
| Main app used local rules while Gemma was connected only to a separate test backend | Main app now connects to existing local Gemma 4 E4B v2 on port 8002 |
| Assistant sent repeated large context and browser timed out before inference | Scoped compact context, relevant confirmations/utility gaps, and a 35-second browser timeout |
| Valid citations did not prevent a model billing-period error | Validate monetary amounts and whole-unit/per-person/payment-period labels; rejected answers explicitly use the local helper |
| Training requirements excluded the installed Transformers 5 runtime | Recorded observed top-level training versions and corrected future Gemma 4 metadata/defaults; historical experiment files remain unchanged |
| Commute refreshes consumed the combined Maps quota | Reserve nearby-search capacity within the cap; owner approved raising the current local cap from 40 to 60 |

“Criteria match” describes checked criteria using known figures. Research fees, usage-based utilities, missing lease dates and actual unit availability still require confirmation. Fresh asking prices do not turn those unknowns into zero or guarantees.

## Pricing verification

All 68 existing catalog plan amounts were rechecked against public operator pages during this review. Foxridge, Windsor, Union and Terrace required rendered browser content; Alight and The Mill were retrieved through the robots-aware HTML adapter. Source timestamps, hashes and plan-specific price locators are retained. Full captures remain in ignored `var/source-refresh/`; the checked-in snapshots contain selected pricing facts. The refresh script stops if a plan price is not supported or a capture is older than one hour.

| Property | Plans | Original billing basis |
|---|---:|---|
| Foxridge | 7 | Whole unit, monthly advertised starting rents |
| Windsor Hills | 7 | Whole unit, monthly advertised starting rents |
| Terrace View | 36 | Per person, published monthly leasing totals |
| Alight | 4 | Per person, 12 installments; annual totals reconciled |
| Union | 11 | Per person, base installment amounts; known utility billing fee separate |
| The Mill | 3 | Whole unit, installments; deposit amounts separate |

Each operator is one Explore entry. The right column shows plan prices or bedroom-group ranges, with original units. Ranges summarize base plan figures; paid room options and additional fees may increase the quote. These checks establish advertised asking amounts, not available units or signed leases. Fee research was not all re-verified during this price refresh.

## Supplied housing guide

The DOCX was read as source material, not instructions. Its inline Word equations contain portions of the price ranges; the importer reads them in sequence and removes superscript citation numbers from addresses/layouts. The guide contributes 47 community and neighborhood references across six areas, with source links and price references explicitly labeled unverified. Six references link to the active catalog properties. Other references do not receive invented coordinates, availability or fit verdicts.

The structured directory is checked in as `data/housing-guide.json`, loaded into a separate `housing_guide` SQLite table and shown at `/#directory`. Search covers community names, addresses and layouts; area filtering is available. Reputation rankings, demographic recommendations, safety claims, fixed bus frequencies and legal interpretations do not become product facts. The original DOCX is unchanged.

## Gemma review

Local base weights and LoRA adapters exist. Existing reports show two training runs against 240 authored synthetic examples; no raw resident reviews were used. Historical base/v1/v2 test reports share templates with training and measure schema, IDs and answer category, not factual grounding. Very low validation loss is not independent evidence of useful generalization.

Six new live questions exercised price, installments, availability, safety, adversarial pricing and fees. All returned schema-valid answers with accepted IDs in that run, but manual inspection found a substantive error: the model called a $1,300 installment a 12-month term price. Some follow-up wording was also awkward. This is why ID/schema checks alone are insufficient.

After strengthening validation, an additional real Grove answer correctly labeled $1,544 as whole-unit monthly asking rent and $808.75 as the per-person subtotal, citing both price and fee sources. A misleading-price prompt returned a labeled local-helper fallback with the correct installment basis. Independent regression tests also exercise invented money, invalid citations and changed billing periods. No additional training was run.

A final Chrome chat request also returned a real Gemma answer identifying Alight's $835 per-person installment and 12-payment schedule. Its limitation text still called freshly checked evidence “old” and used awkward phrasing. That is a remaining quality defect, not evidence that the current price capture is stale. No application console errors were observed. The correct answer format and numeric guards do not substitute for human claim-level evaluation.

Next model work should use independent human-written prompts with the actual production context shape and reviewed targets. Evaluate each monetary claim, payment period, subtotal scope, assumptions, uncertainty and citation support. Split by property/source/time and retain an untouched test set. Keep current rents in retrieval, not training weights. The old `/api/v1/ai/explain` runtime remains separate and unconfigured; configuring chat does not wire that endpoint.

## Nearby places and verification

Property details now support six categories, 1/2.5/5 km radii, up to eight distance-ranked results, straight-line distances, numbered markers and directions links for walk/drive/bike/transit. Directions originate at the property and use destination place IDs. Provider attribution and the limitations of straight-line distances remain visible. Google content is not added to SQLite, saved briefs, assistant context or training data.

Live Chrome checks verified restaurants, gas stations and groceries around Foxridge, marker focus and the driving/walking link parameters. A 1 km restaurant search verified the empty-results message. A second grocery query verified that results recover after changing category/radius. Five additional live searches were used after approval to raise the quota; the earlier cap-exhausted state was also observed. Unit tests verify payload types, radius validation, calculated distances, failure handling, quota limits and reserved Places capacity. No application console errors were observed in the final nearby flow.

The next Maps stages are detailed in [MAPS_PLAN.md](MAPS_PLAN.md): explicit travel-time checks for selected essentials, element-based matrix budgets, grocery reach comparisons, optional place details and clearer spend controls.

## Reproduce and maintain

```powershell
Set-Location C:\commonground-vt-main
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/frontend_adapter.test.cjs
.\.venv\Scripts\python.exe tools/build_frontend.py
.\.venv\Scripts\python.exe tools/backend/verify_release.py --python .venv-release-check/Scripts/python.exe --port 8004

# Preview a future checked-in catalog update; apply only after a database backup.
.\.venv\Scripts\python.exe tools/backend/sync_catalog.py
.\.venv\Scripts\python.exe tools/backend/sync_catalog.py --apply
```

Verification: **79 Python tests and 8 frontend tests passed**, plus a clean production-runtime HTTP flow with fresh temporary SQLite. That flow checked authentication, 68 plans, 47 guide references, 350 buildings, weekly GTFS routing, workspace/checklist/brief persistence, local helper and export/trash/restore. One upstream Starlette/httpx deprecation warning remains.

The release verifier was also fixed for Windows venv launchers: shutdown now terminates its own process tree so a child Python server cannot keep temporary SQLite files locked. The clean HTTP check passed after that fix. The existing daily Maps ledger was retained; final inspection showed 52 Routes and 6 Places attempts against the approved cap of 60 for the UTC day (five Places attempts belonged to this review after approval).

Operational test artifacts under ignored `var/`: `release-housing-review.json`, `assistant-review-cases.json`, `assistant-review-final.json`, and UI screenshots. The model server must remain running on port 8002 for model answers. Cross-device firewall traversal, cloud deployment/persistence, full fee and availability coverage, review-use authorization, and production AI accuracy remain unverified.


## Follow-up: all guide housing in Explore, schedule removal and Compare explanation

All 47 guide communities/neighborhoods now appear once each in Explore: 68 operator plans across the original six properties, plus 41 explicitly unverified reference candidates. Reference candidates retain the DOCX layouts, addresses and price descriptions, support shortlist/comparison, and have no invented numerical quote or coordinates. Nearby lookup rejects missing coordinates before spending quota. The guide directory is still available separately.

Removed schedule navigation, class editor, sample schedule, route-date controls, preference controls and class-based comparison/guide rows. Existing browser/server schedules are no longer restored into active state; current comparison/workspace requests send empty commitments. Historical snapshots remain unchanged. Legacy backend routing contracts remain compatible with saved data.

Compare now calls the connected `/assistant/messages` service rather than the unconfigured legacy `/ai/explain` runtime. It includes only the selected candidates, discards responses when the revision or shortlist changes, and identifies actual model responses separately from a deterministic fallback. The fallback summarizes selected properties even when the question mentions billing. Reference figures are not promoted into validated current prices.

Backups before this additive migration: `var/backups/pre-explore-update-20261024-213616/`. Fresh release report: `var/release-explore-update.json` (109 candidates, 47 properties, no live Maps calls). No commit or push was performed.


The live mixed-property comparison exposed a truncated JSON response: the local GPU server stopped generation at 20 seconds. Its bounded generation window is now 45 seconds, model transport 50 seconds (55-second total stream guard), and assistant browser timeout 65 seconds. Assistant instructions request an answer under 90 words and a compact JSON response. Invalid/truncated responses still fail validation and use the explicit local summary; validation was not weakened.

Verification after the Explore and schedule changes: 82 Python tests and 11 Node adapter tests passed, plus the fresh-storage production HTTP release flow. Chrome verified the 47-option count, new-property details, shortlisting, comparison, labeled guide pricing and no schedule navigation/commute rows. Screenshots are saved under `var/roomwise-explore-guide-update.png` and `var/roomwise-compare-guide-update.png`.


Final local Gemma diagnostic: after allowing complete generation, the tuned model also produced a schema echo followed by an answer that relabeled Alight's installment as monthly. This correctly fails JSON/monetary validation. The mixed Alight/Edge browser test therefore displays the cited local research summary, not a claimed Gemma answer. The model's comparison reliability remains a limitation; retraining was not performed and validation was not relaxed. Compare itself now has a useful complete response with clear provider identity when this happens.
