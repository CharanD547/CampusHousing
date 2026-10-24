# Exact pricing and resident-review gaps

Audit: October 24, 2026. Based on the running catalog, separate housing observations, review database and current source-policy inspection. This is a field-level backlog, not new pricing or legal clearance.

## Update: pricing research port (Oct 24, 2026)

The pricing research audit has been ported into `data/housing-seed.json` by `tools/backend/port_pricing_research.py`. Backend work items 1–4 below are implemented in `roomwise.domain.costs.fee_breakdown`. Each offer now carries:

- **`fees`:** classification, timing, scaling basis, amount range, inclusion flag, credit target and source.
- **`utility_matrix`:** with its own `utility_source_id`.
- **`price_confidence_tier`**
- **`advertised_range`:** named plans with ranges.
- **`source_conflicts`**
- **`operator_questions`**

Fifteen `research_observation` sources were added, all with `refresh_policy: manual_only`.

**Counted in arithmetic:** a fee counts only when every source it depends on is reviewed against stored snapshot text. Two facts meet that bar today:

| Fact | Evidence in the reviewed snapshot | Effect |
|---|---|---|
| Union $6.79 utility billing administrative fee per installment | `union-plans`: every plan's "Total Monthly Leasing Price" is base rent + $6.79 | `known_recurring_subtotal` now matches the portal total, e.g. B2 $1,420.79 |
| Alight annual totals include $155 in mandatory fees | `alight-plans`: "Total price: $10,175 - $10,415 … East $835 West $855"; 2B $11,615 - $12,143 for $955 / $999 | `annual_total` set to $10,175 / $10,415 / $11,615; the $155 is a per-term fee |

The Mill's deposits were already reviewed and now flow into the refundable-deposit bucket.

**Recorded but not counted** (research observations, pending review):

- Foxridge and Windsor Hills fee schedules, move-out inspection fees and deposit ranges
- Credited reservation payments
- Terrace View per-installment fees, whose inclusion is unconfirmed
- Advertised plan ranges for Foxridge (14 plans), Windsor Hills (6) and Terrace View (per-bed listings)
- Union application, admin, deposit and insurance terms, and utility inclusions
- The Mill's per-applicant basis for the application fee

**Conflicts kept open rather than resolved:**

- Alight's one-sheet ($829 / $849 / $949) versus the reviewed rates page ($835 / $855 / $955)
- Union's $6.79 versus a cached $6.44, and annual versus "11 Month Lease"
- Windsor's deposit: $300–$500 (operator PDF) versus $400–$1,500 (Apartments.com)
- Windsor's $40 amenity fee
- Foxridge's reservation credit: toward rent or toward the deposit
- Foxridge's "Shared Pricing" figures versus its whole-unit leases
- The Mill's "By-The-Bed" listing badge versus its joint lease

**To promote a research value:** retrieve and store the source snapshot, review it, and set the source's `review_status` to `reviewed`. The value then counts with no code change.

`CatalogRepository` seeds with `INSERT OR IGNORE`, so an existing `var/catalog.sqlite3` keeps its old offer bodies. A fresh data directory picks up this seed.

The tables below describe the state before this port. The per-offer `unknowns` and `operator_questions` in the seed are now the current list.

## 3. Complete pricing and availability

### What is actually missing by property

| Property / catalog records | Established in the catalog | Still missing or unresolved |
|---|---|---|
| Foxridge: `foxridge-1`, `foxridge-2`, `foxridge-3` | Bedroom categories 1/2/3 and property/source identity | Exact named plan/unit; base amount; person/unit basis; billing frequency/payment count; exact dates; lease responsibility; bedroom/occupancy arrangement; applicable fees/deposit; current inventory |
| Terrace View: `terrace-1`, `terrace-2`, `terrace-4` | Bedroom categories 1/2/4 and person-based pricing scope | Exact tier/plan/unit; numeric base amount; payment frequency/count; lease dates; individual/joint responsibility; actual room/occupancy setup; fee inclusion; current inventory |
| Windsor Hills: `windsor-1`, `windsor-2`, `windsor-3` | Bedroom categories 1/2/3 and property/source identity | Exact plan/unit, amount, person/unit basis, billing frequency/count, lease dates/responsibility, occupancy setup, applicable fees/deposit and availability |
| Alight: East, West, Standard two-bedroom | $835 / $855 / $955 per person per installment; 12 payments; individual/private-room scope; Aug 18, 2027–July 24, 2028 | Exact mandatory fee allocation and totals; utilities/electricity by plan; deposits and upfront charges where applicable; which charges are included; actual room availability and ability to place a household together |
| Union: S1 Furnished, B2 Deluxe Furnished, C1 Furnished | $1,678 / $1,414 / $1,340 per person per installment; private-room scope; Aug 16, 2027–July 17, 2028 | Payment count; individual/joint lease responsibility; itemized reconciliation of base rent versus higher displayed leasing total; utilities, recurring/upfront charges and deposits; exact offer applicability and household availability |
| The Mill: one/two/three bedrooms | $1,100 / $1,300 / $1,680 per apartment per installment; 12 payments; whole-unit responsibility; deposits $800 / $900 / $1,050; $35 application fee | Exact lease start/end dates for the offer; application-fee charging basis; electricity/internet costs; legal/contractual occupancy permission; current unit availability; any additional required costs |

There are **nine null-price records**, but all 18 records still have some unresolved costs, scope or availability. Numeric base rent is not a complete cost-of-living quote. These catalog categories also do not cover every plan advertised by each property.

### Evidence already found, but not yet reconciled

The following are earlier research observations in `data/housing-research-observations.json`. They are intentionally excluded from comparison totals. The current page inspection does not constitute a fresh verification of every linked fee document or live unit inventory.

- **Foxridge:** named-plan ranges were observed for Burruss, one bedroom ($1,359–$2,083); Grove, two bedrooms ($1,455–$2,436); Willow, three bedrooms ($1,728–$2,900). A promotional person-based statement conflicts with other pricing context. Required action: match a specific plan/unit, dates, occupancy and billing basis. Do not use the range minimum as an available quote.
- **Foxridge fees:** observed monthly trash $7, internet $65 and billing $1.50; application $35 per adult, administration $200 and a $200 reservation payment credited toward rent; deposit range $400–$1,500. Required action: establish applicability/inclusion and reconcile plan-specific deposits. A reservation credit must not be counted again as an additional term cost. Insurance remains provider-dependent.
- **Windsor fees:** observed monthly trash $9 and billing $1.50; application $30 per adult, administration $200, reservation credit $200, deposit $300–$500 and provider-dependent insurance. Required action: obtain an exact base-rent/term quote, match the disclosure to it and resolve screening-dependent amounts. Earlier inventory access redirected to sign-in; no private access was bypassed.
- **Terrace specific example:** `1x1 Tier 3` displayed a $1,450 total monthly leasing price, $200 deposit and Aug 21, 2027–July 31, 2028 dates. This is not a verified base-rent replacement for the generic one-bedroom category. Required action: preserve it as a separate specific offer if current evidence supports it, then reconcile price composition and payment schedule.
- **Terrace fees:** observed $5 utility billing, $40 technology and $10 trash per installment; administration $150 per primary leaseholder and application $50 per applicant; variable electricity/shared-space electricity/insurance; deposit up to two times rent. Required action: establish which are already included in the advertised leasing total and why the selected-plan deposit differs from the general range. Do not add included charges twice.

Official source entry points: [Foxridge](https://www.foxridgeliving.com/floorplans/), [Windsor Hills](https://www.windsorhillsapts.com/floorplans/), [Terrace View pricing](https://terraceviewblacksburg.com/pricing). Field observations retain their exact fee/inventory URLs in the research file.

### Backend work needed after obtaining evidence

1. Create exact offer identities rather than silently converting broad categories into whichever plan is cheapest. Retain plan/tier, bedroom/bathroom scope, unit/availability identifier if public, dates, quote validity and occupancy conditions.
2. Extend the current fee representation. Catalog offers currently carry an `upfront` list; the cost calculator primarily calculates base rent and preserves unknowns. Add explicit recurring/one-time/refundable/optional classifications, billing frequency, per-person/unit/applicant basis, applicability, included-in-quote flags, credits and field-level provenance. A separate research note does not implement fee arithmetic.
3. Calculate distinct known recurring subtotal, one-time nonrefundable cost, refundable cash requirement, credits and base term payments. Keep variable/unknown charges unknown. Preserve installment versus calendar-month units and scenario-based household splitting.
4. Represent screening-dependent deposits and conditional fees as ranges/conditions, not one exact guaranteed amount. Separate advertised price, operator quote and confirmed availability with timestamps.
5. Reconcile contradictory pages with an explicit review record. Update the maintained seed and running database transactionally; do not mutate saved briefs or let model-generated values update authoritative prices.
6. Add refresh/change detection with reviewed timestamps, source access failures and stale/conflicting states. A successful page download alone is not a completed price review. Inventory requires its own freshness rule.
7. Test fee inclusion/credits, mixed periods, per-unit splitting, deposit conditions, stale evidence, missing utilities, household occupancy and historical snapshot preservation. Update frontend totals/labels alongside the API contract.

### Exact information to request from an operator

For each selected layout/unit and intended stay: a dated itemized quote identifying base amount and billing basis; all payment dates/count; lease start/end; mandatory recurring and upfront charges with charging basis; included versus usage-based utilities; refundable deposit/screening conditions; credits/concession conditions; lease responsibility/occupancy limits; and whether that unit or set of rooms is available for the household. Roomwise does not need banking data, ID documents or a completed application to record this evidence. Sending requests to property staff would require authorization.

**Completion condition:** each record presented as a comparable priced offer has exact supporting evidence and correct charge arithmetic. Where evidence is unavailable, keep it as an explicit unknown/research lead. Current availability cannot be inferred from a floor-plan page alone.

## 4. Resident reviews and review-based AI

### Actual dataset status

| Item | Audited state |
|---|---|
| Total corpus | 720 unique records across 30 schools |
| Text coverage | 676 full-text records; 44 rating-only records |
| VT subset | 67 records, all marked full-review text |
| Tentative VT mappings | Foxridge 12; Alight 6; Union 4; Terrace View 3 |
| Remaining VT records | 42 have no tentative mapping to the six-property catalog in the matching table |
| Approved product mappings | None; the 25 candidates all require scope verification |
| Windsor Hills / The Mill | No approved matches; this does not prove reviews do not exist |
| Permission metadata | All 720 records say `reuse_permission=not_established` |
| Verification | Opinions are marked subjective/not independently verified |
| Product/model use | No public review-text API, review-backed summary or review ingestion into the model |

The remaining 653 non-VT records are not VT evidence. A review subject can describe a landlord, property, building or former management rather than the exact offer. School/name similarity is insufficient to combine it with a specific unit. Alight East/West is a concrete unresolved distinction.

### Permission and privacy information needed

The current [OCR terms](https://www.offcampusreview.com/terms-conditions), dated September 1, 2026, state that contributors retain their content and grant rights to OCR. That inspection did not establish a Roomwise reuse license. Robots access and publicly readable content do not by themselves settle permitted republication/model use; this is not legal clearance.

Establish the basis for each intended activity separately: local retention, display/excerpts, summaries, embeddings/retrieval, inference processing, training and derivative adapter distribution. Preserve evidence of allowed use, scope, restrictions, attribution, expiry and removal obligations. Permission could come through applicable licensing, authorized platform arrangements or an appropriately authorized original contributor dataset; do not assume all uses are covered together. Platform permission alone must not be assumed to settle every contributor right.

The collector omits structured author/account/email fields, but free-text reviews may still contain personal details. It has not established that all text is de-identified. Review and minimize names, contact details, precise unit identifiers, allegations and other unnecessary sensitive content before product/model use. Do not describe the corpus as privacy-cleared or verified resident identities.

### Data and API work still needed

- A reviewed canonical-property mapping with source evidence, reviewer, date and uncertainty. Preserve landlord-wide versus property-specific scope, management period and exact East/West distinctions. Leave ambiguous records unmatched.
- Per-record allowed-use decisions rather than a global enable switch; source review/page IDs, review/lease period, text scope, attribution, last-seen/update data and content hash.
- Deduplication and source-update/removal handling. Existing upsert and first/last-seen fields are useful foundations, but do not implement a full permission/removal propagation workflow.
- A gated retrieval API filtering by approved property, use permission, date and usable evidence. Report total reviews, matched reviews, text-bearing reviews, exclusions and review periods. Do not fabricate text for rating-only entries.
- Retention/takedown logic across raw research, excerpts, indexes, embeddings, caches, summaries, training exports and backups. If material enters training, define retraining/retirement handling; deleting one source row does not prove its influence vanished from weights.

### AI work still needed

**First build source-grounded retrieval and summaries.** Supply only a small permitted property-specific evidence set, treat review text as untrusted data, require citations and distinguish individual reports from supported recurring themes. An AI summary must disclose dates, small sample size and contradictory accounts. No reviews must yield insufficient evidence, not an invented “wish I knew” section.

**Fine-tuning is a separate later step.** A raw review dump is not a supervised training dataset. Create reviewed input/target examples and aspect/uncertainty labels; relevant topics can include billing/value, management, quietness, amenities, move-in/out, roommate/lease issues and commute reports. Keep current prices/routes authoritative in the deterministic catalog/provider layers. Split real examples by property/source/time and remove duplicates so evaluation does not reward memorization.

Evaluate citations against actual supporting passages, temporal/property scope, false consensus, hallucinated facts, prompt injection, personal-data leakage and unsupported legal/safety conclusions. Reported safety feelings remain individual opinions, not an official safety rating. Compare the untuned baseline and any tuned adapter on genuinely held-out examples; valid JSON alone is insufficient.

**Completion condition:** documented allowed use, reviewed matches, privacy screening, permission-aware retrieval, tested updates/removals, and useful cited outputs with real evaluation. Until then the existing deterministic checklist/local helper can continue without review content.
