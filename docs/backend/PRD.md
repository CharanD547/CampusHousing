# Roomwise — Backend Product Requirements Document

**Version:** 1.1 — backend-only working scope  
**Date:** October 24, 2026  
**Owner:** Backend / data / AI / Google Cloud team  
**Status:** Implementation specification; features not assumed complete  
**Scope:** Backend only; frontend navigation/layout and duplicated integrated-PRD appendix removed. The supplied backend PRD remains the requirements source.

## 1. Backend mission and boundaries

Provide an evidence-grounded decision API for housing prices, shared-household fit, class-journey routing, comparisons, Gemma-based explanations, saved decisions, and optional DormToDoor action plans. The backend is the authoritative source for calculation, price provenance, routing evidence, and model response validation; the frontend owns presentation and guide navigation.

**Backend owns:** validated catalog, source audit and corrections; campus/building records; cost/bedroom and schedule constraints; routing adapters and provider limitations; map sample values; structured Gemma tool access; permitted reviews/grounding; persistence where applicable; stable API schemas; secrets/cost controls; tests and deployment.

**Backend does not own:** client visual layout or navigation, browser-local data promises, unsupported legal or safety conclusions, or unlicensed redistribution of reviews.

**Priority:** P0 correctness and real end-to-end route + Gemma demonstration. P1 DormToDoor checklist support, grounded neighborhood answers, approved feedback. P2 second campus, lease scanner, vision and 3D features. Accuracy is a release blocker.

## 2. Architecture and bounded services

```text
React application (frontend)
    |
    v
FastAPI API service (Cloud Run or existing compatible server)
    +-- CatalogRepository -> curated properties/offers + provenance
    +-- CampusRepository -> verified buildings and supported campuses
    +-- ComparisonService -> deterministic cost, bedroom and fit checks
    +-- RoutingAdapter -> selected supported mapping/transit provider
    +-- EvidenceRepository -> cited source metadata and policy checks
    +-- GemmaOrchestrator -> selected supported inference runtime + bounded tools
    +-- GuideService -> baseline checklist + evidence-backed optional Gemma items
    +-- Workspace/BriefStore -> Firestore or clearly scoped local adapter
```

Keep current working prototype frameworks/adapters when reasonable; no migration merely for fashion. Google Cloud Run, Firestore and Cloud Storage are candidate managed services rather than claims of existing configuration. Keys remain server-side; an appropriately restricted Maps browser key is separate.

## 3. Data provenance, catalog and price corrections · P0 blocker

- Catalog records distinguish `property`, `specific offer`, `area`; locations indicate entrance/address/area-center provenance.
- Every numeric asking price has amount, currency, person-or-unit basis, calendar-month/installment/other frequency, layout, applicable term, payment count if known, exact source link and last reviewed date.
- Store recurring mandatory, optional, one-time nonrefundable and refundable deposit amounts separately. Null stays unknown, never zero.
- A price older than seven days is flagged stale per the source PRD's **product policy**, not presented as current budget fit.
- Pricing computations use deterministic code and preserve the advertised billing period. Share whole-unit rent only as an explicit what-if scenario; enforce bedroom incompatibility independently.
- When operator sources conflict or change, flag for manual source review and run catalog correction script; do not silently overwrite source facts with LLM-generated amounts.
- Updating live storage must actually update deployed data; tests and seed files alone do not constitute a correction.
- Saved decision briefs are immutable snapshots; a catalog update only changes current comparisons.
- Respect source website access, storage/reuse permissions and attribution obligations. No private or employer-controlled OffCampusReview export without approval.

## 4. Campus locations and routing · P0

- Initial supported scope is VT/Blacksburg. A second university is **not** supported merely because a map center can move; it requires campus buildings, curated housing, reviewed prices and tested routes.
- Verified buildings have stable IDs and source-backed coordinates. Never guess an ambiguous destination.
- Route requests honor the user-selected modes, building weekdays/arrival time, buffer, and a clearly declared representative routing date.
- Each response records origin, destination, mode, route date, wait/walk/transfer scope when provided, provider, and supported/unavailable/unsupported status.
- Distinguish absent provider support from physical impossibility. Never invent transit for dates beyond timetable support or replace unavailable future dates with present ones without disclosure.
- For N commitments calculate support count, per-commitment evidence and limiting commitment; a single good trip does not mean a weekly plan works.
- Map shading returns only measured candidate/sample-point travel data, with no fake continuous isochrone.
- Cache only where provider terms allow; key results by full route context and freshness.

## 5. Comparison and recommendation rules · P0

1. Validate campus, inputs, travel modes, dates, positive household and budget limits, and 1–10 schedule commitments.
2. Load active source-audited offers. Normalize **presentation** of billing basis without assuming payment count or turning installments into monthly rent.
3. Calculate known costs and clearly list unknown mandatory charges. Determine bedroom/individual-contract hard conflicts.
4. Resolve route estimates for supported modes and requested class commitments, with partial/error outputs when evidence is missing.
5. Classify each candidate `documented_fit`, `conflict`, or `insufficient_evidence`. A low base subtotal is not proof of budget compliance.
6. Return reason codes, numeric results, route coverage, evidence IDs, source date and request revision. Incomparability/ties permitted; users remain in control.

Never rank neighborhoods on demographic proxies, safety claims or unverifiable property-quality generalizations. Filter hard conflicts ahead of subjective preferences. Do not force a winner.

## 6. Gemma model responsibilities · P0

The genuine Gemma model is the primary **explanation assistant** once real inference is configured and proven. The original prototype previously used Gemini orchestration and a Gemma review component; a proposed reallocation of responsibility must be implemented, not merely described.

- Input: validated preferences, shortlisted candidate comparisons, source-linked facts and bounded tool access.
- Allowed tools: `get_commute(candidate_id, commitment_id, mode)`, `nearby_places(candidate_id, category)`, `get_area_data(candidate_id)`; additionally `get_offer_evidence` and `get_comparison` are useful if implemented and documented.
- Output: structured explanations with property ID, summary, preference relevance, sources, limitations, unanswered question, tool result refs and actual model ID.
- Deterministic backend code handles currency, arithmetic, budget thresholds, room counts, schedule coverage and factual fit status.
- Retrieved reviews, listing pages and user uploads are untrusted **data**, not model instructions. Validate JSON against a schema; disallow source IDs not retrieved. Bound tool iteration count, token spend, concurrency and timeout.
- If inference fails, return `ai_unavailable` with meaningful reason; preserve comparison and checklist. A fixture answer is not a genuine model run.
- Google Search Grounding via Gemini, if added for neighborhood questions, stays **separate** from Gemma inference. Search snippets cannot overwrite audited prices.

## 7. DormToDoor supporting services · P1

The guided interface is frontend-owned; backend supports it through existing preference/commitment/comparison APIs plus a checklist endpoint. **Do not build a separate recommendation system or property catalog.**

Checklist generation sequence:

1. Take a chosen candidate/offer, current revision, preferences, schedule, comparisons and evidence IDs.
2. Produce a safe deterministic checklist by category: Money, Lease, Roommates, Commute, Move-in.
3. Insert actionable questions for actual unresolved unknowns (fee schedules, utilities, term installments, deposits, roommates' responsibility, verified transportation conditions, availability, move-in logistics).
4. Optionally ask Gemma to rewrite/prioritize items or add property-specific questions **only if** evidence supports them; every generated property-specific assertion includes an evidence ID or is labeled general advice.
5. Keep editable checklist IDs stable and preserve user statuses/notes on regeneration; never mark actions done automatically.
6. Summarize `What students wish they knew` only from permitted, consented or appropriately licensed reviews with citation and sample-size caveat; otherwise return insufficient evidence.
7. Return a typed response that works with Gemma and reviews disabled.

No mandatory user accounts, ID, banking data, payments, lease execution, application submission, automatic calendar/email import or legal determinations.

## 8. Source-backed reviews and third-party enrichment · P1/P2

- OffCampusReview is a possible review source only if appropriate rights/approval are in place, not a required private dataset.
- Google Places can support discovery and limited review display **subject to current provider limits, attribution and retention terms**; do not design bulk text harvesting into the core architecture.
- Separate external discovery/grounding (e.g., Gemini with Google Search capability if configured) from Gemma's review interpretation. Search sources must be cited, and unlicensed text should not be republished or permanently stored.
- `ReviewEvidence` should include original source context, period, permission/retention status, subjective/unverified label, extracted topic and tool provenance.
- AI topics may span affordability/value, management, quietness, social environment, commute, amenities, move-in/move-out and living conditions. Never reduce reviews to maintenance alone or manufacture consensus.
- P1 must not delay P0 price integrity and commute support.

## 9. Persistence, security and privacy

- Store versioned editable workspaces separately from immutable decision briefs. Revision checks prevent delayed route/model results overwriting new state.
- Session/local-only persistence is acceptable for the hackathon **if clearly advertised**. If server-backed, define access controls, retention/deletion policy and prevent access to other participants' work.
- Upload or model-processing disclosure must state what leaves the device, provider and retention scope. Do not collect exact residence, student ID, account credentials or ID documents for the default journey.
- All private keys and service credentials are injected server-side via protected configuration/Secret Manager as appropriate. Never include them in tracked source, browser responses or sample cURL commands.
- Do not log entire student schedules, raw reviews without permission, uploads, or sensitive payloads to public telemetry.
- Bound API rate/concurrency and provide an owner-visible disable switch for chargeable inference/routing. Billing alerts do not enforce a cap.

## 10. Performance, failures and operations

Targets to test rather than achieved SLAs: usable app shell around 3s (frontend concern), initial bounded commute comparisons around 15s, useful model explanation around 30s. Return progress and partial results when possible. APIs carry `error.code`, `retryable`, and `request_id`; missing data has a distinct response from failures. Implement retry backoff and idempotency for billed operations and saved objects. External map, route, source and AI outages must not destroy comparisons or historical briefs.

## 11. Backend test plan

| Test | Required assertion |
|---|---|
| Price source stale >7 days | Cannot imply documented current affordability |
| Price correction | Running catalog fixed; frozen brief unaffected |
| Whole unit vs per-person lease | Unit division marked scenario; no conversion to offered per-person quote |
| Missing utilities | `unknown_costs` not zero; no all-in claim |
| Three private rooms / two-bedroom layout | Bedroom hard conflict irrespective of arithmetic |
| Transit date out of support range | Route explicitly unsupported/unavailable, not silently substituted |
| Two commitments / one supported | Coverage count 1/2, no full-schedule fit |
| Invalid campus building | Validation error, no silent guess |
| Prompt injection in review/listing | Cannot modify instruction hierarchy or invent pricing |
| Source missing / contradicted | Evidence limitation returned and visible |
| Stale revision/model response | Rejected or marked obsolete |
| Gemma failure | Deterministic comparisons and generic checklist remain |
| No authorized reviews | `wish_i_knew` unavailable rather than generated quotes |
| Guide checklist regenerated | User status and notes preserved |
| Source data retention policy | No forbidden persistent review copies |
| Missing key / exhausted budget | Safe reduced-mode response with actionable error |
| Fresh deploy with fixtures/config | Correct model status, source dates and API paths reproducible |

## 12. Backend delivery plan

| Wave | Build | Exit condition |
|---|---|---|
| BE-A | Define OpenAPI schemas, typed fixtures and failure codes | Frontend can mock the entire flow |
| BE-B | Audit catalog and pricing, verified buildings | Published prices have complete evidence or show unknown |
| BE-C | Deterministic cost/room comparison and routing adapter | Two-class test with partial/unsupported travel works |
| BE-D | Gemma runtime + tool-bounded explanation | Genuine model output with real tool evidence and citations |
| BE-E | Workspace/brief persistence and corrective scripts | Frozen snapshots + correction regression pass |
| BE-F | DormToDoor checklist service and review gating | Safe checklist works AI-off; optional grounded additions work if available |
| BE-G | Google Cloud deployment, quotas, monitoring, integration | Real hosted API stable within event spending controls |

**Suggested split:** Backend developer A: catalog, cost engine, routing and API. Backend developer B: Gemma orchestration, checklist, persistence, Google Cloud and source policy. Agree on one data-schema owner.

## 13. Release gates and known dependencies

- Current source PRD identifies VT as the only supported MVP campus and treats nationwide mode as later validation work.
- True Gemma access/runtime is not established by the PRD alone; log tested model/version, deployment route, cost and a real successful inference before claiming it as a judged feature.
- Google provider support for desired travel modes, times and review access must be proven with actual requests.
- The source deadline context is October 25, 2026 at 12:30 PM local; verify organizer schedule and cut P1 before weakening P0.
- Publish open-source application code, safe synthetic fixtures, deployment steps and documented limitations; exclude private uploads, schedules, proprietary reviews and secrets.

## Shared integration contract — binding for both teams

The following is a **proposed v1 interface**, not evidence that these endpoints already exist. Both teams should agree on the JSON schemas before implementation, save versioned fixtures in `contracts/`, and maintain backward compatibility for the hackathon demo.

### Canonical objects

- `Campus`: `id`, `name`, `timezone`, `buildings[]` (each with verified identifier, label, coordinates, source).
- `Preferences`: `campus_id`, `monthly_budget_per_person`, `household_size`, `private_bedroom_required`, `requested_bedrooms`, `individual_lease_required`, `travel_modes[]`, `max_commute_minutes`, `arrival_buffer_minutes`, `move_in_date?`, `move_out_date?`, `priorities[]`, `revision`.
- `Commitment`: `id`, `building_id`, `weekdays[]`, `arrival_time_local`, `arrival_buffer_minutes?`.
- `Candidate`: `id`, `type: property|offer|area`, `property_name`, `address?`, `coordinates`, `coordinate_basis`, `offer?`, `data_status`, `sources[]`.
- `Offer`: `id`, `layout`, `bedrooms?`, `price: {amount, currency, basis: per_person|whole_unit, frequency: calendar_month|installment|other, payment_count?, term?, source_id, last_reviewed_at}`, `fees[]` (separating one-time, mandatory, optional and refundable), `unknown_costs[]`.
- `CommuteEstimate`: `candidate_id`, `commitment_id`, `mode`, `minutes?`, `status: supported|unsupported|unavailable`, `route_date`, `provider`, `context`, `coverage_notes[]`.
- `Evidence`: `id`, `source_type`, `source_name`, `url?`, `observed_at`, `supports`, `excerpt?`, `license_or_reuse_scope?`.
- `Comparison`: `input_revision`, `candidate_results[]` with `fit_state: documented_fit|conflict|insufficient_evidence`, cost breakdown, commute coverage count, hard conflicts, unresolved questions, evidence IDs.
- `AIExplanation`: `input_revision`, `model_id`, `status`, `candidate_explanations[]` including reasons, limitations, next questions and evidence IDs; model must not generate arithmetic as ground truth.
- `GuideProgress`: `current_step: 1|2|3|4`, `completed_steps[]`, `preferences_revision`, `commitments[]`, `selected_candidate_ids[]`, `checklist[]`, `updated_at`.
- `ChecklistItem`: `id`, `category: money|lease|roommates|commute|move_in`, `title`, `details?`, `status: not_started|in_progress|done|not_applicable`, `notes?`, `evidence_ids[]`, `needs_confirmation`, `origin: generic|deterministic|gemma|user`.
- `DecisionBrief`: immutable `id`, `saved_at`, snapshot of inputs, evidence timestamps, comparisons, checklist, selected offers, AI status, and unresolved questions.

### Proposed endpoints

| Method / endpoint | Purpose | Owner |
|---|---|---|
| `GET /api/v1/campuses` | Supported campuses only; no phantom campus support | Backend |
| `GET /api/v1/campuses/{id}/buildings` | Verified building destinations | Backend |
| `GET /api/v1/candidates?campus_id=...` | Curated property/offer/area inventory and provenance | Backend |
| `POST /api/v1/comparisons` | Validate inputs, cost basis, constraints, supported commute evidence; return `input_revision` | Backend |
| `POST /api/v1/ai/explain` | Gemma-powered explanation using existing comparison/evidence IDs | Backend |
| `GET /api/v1/evidence/{id}` | Source context available to user; subject to provider terms | Backend |
| `PUT /api/v1/workspaces/{id}` | Save current preferences, commitments, shortlist, guide progress, questions | Backend if server persistence; otherwise frontend local storage adapter |
| `POST /api/v1/briefs` | Save immutable decision snapshot | Backend if server persistence; otherwise frontend local snapshot adapter |
| `GET /api/v1/briefs/{id}` | Retrieve frozen decision brief | Backend if server persistence; otherwise local adapter |
| `POST /api/v1/guide/checklist` | Generate deterministic baseline + optional grounded Gemma items | Backend |
| `GET /api/v1/health` | Readiness of API and optional dependencies without exposing secrets | Backend |

For the hackathon, an in-browser persistence adapter is permitted by the source PRD if **explicitly labeled local-only**. Do not expose mock endpoints as live services. The frontend can run on fixture JSON while the backend is being developed, but must clearly label fixture mode.

### Request / response principles

- All writes and comparisons include a `revision` (or a stable request ID) to reject stale responses.
- Never turn unknown rent, fee, route, or review fields into zeros or invented defaults.
- Server sends typed `status`, `error.code`, `error.message`, `retryable`, and `request_id`; frontend presents recoverable states.
- AI-generated text is evidence-linked and separately identified from reviewed facts, user notes, estimates and general advice.
- Source timestamps and price billing basis travel end-to-end unmodified.
- Backend validates inputs and authorization; frontend validation is for usability only.
- No API key, private schedule, unapproved review data, or identifying document is placed in a public log or repository.

### Contract example — `POST /api/v1/comparisons`

```json
{
  "campus_id": "vt",
  "revision": 7,
  "preferences": {
    "monthly_budget_per_person": 1100,
    "household_size": 2,
    "private_bedroom_required": true,
    "travel_modes": ["walk", "transit"],
    "max_commute_minutes": 30,
    "arrival_buffer_minutes": 10
  },
  "commitments": [
    {"id": "c1", "building_id": "example-building-id", "weekdays": ["mon", "wed"], "arrival_time_local": "09:00"}
  ]
}
```

Response shape (illustrative, not a real property result):

```json
{
  "revision": 7,
  "status": "partial",
  "candidate_results": [
    {
      "candidate_id": "demo-001",
      "fit_state": "insufficient_evidence",
      "price_label": "Base installment; mandatory fee information incomplete",
      "known_recurring_subtotal": 1025,
      "unknown_costs": ["electricity"],
      "supported_commitments": 1,
      "total_commitments": 2,
      "evidence_ids": ["demo-source-1"]
    }
  ],
  "missing_data": ["One commitment lacks a supported transit route"]
}
```

### Working agreement / definition of integration done

1. Both teams commit matching fixture files to `contracts/fixtures/` and review schema changes together.
2. A single path from onboarding through schedule → comparison → Gemma explanation → checklist → saved brief succeeds against the real backend.
3. A price correction changes the active comparison but never a frozen brief.
4. Simulated route/AI outages and stale responses do not erase user work.
5. The app distinguishes live, sample and unsupported data in the UI and demo.
