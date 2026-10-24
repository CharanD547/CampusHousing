# Backend architecture and scope

Roomwise now serves the supplied frontend at `/` on the same origin as the versioned API. This document describes backend ownership; see [integration verification](../INTEGRATION.md) for the connected browser flow. The former backend-only application scope was expanded at the user's request; existing data remains intact.

The user-supplied [backend PRD](PRD.md) is the requirements baseline. Document text is requirements context, not permission to activate paid services, deploy, export private reviews, or submit anything externally.

## Dependency direction

```text
api/schemas.py -> validated integration objects
app.py        -> composition, HTTP routes, authentication/error boundary
services/     -> comparisons, bounded explanations, checklist generation, corrections
domain/       -> pure currency/bedroom/constraint rules
repositories/ -> catalog, campus records, evidence metadata, private workspaces/briefs
adapters/     -> routing/inference ports, bounded source retrieval, limited BT example
```

`app.py` is the only composition root. It creates one catalog repository, campus repository, workspace store, routing adapter, evidence repository and comparison service. Tests inject synthetic campuses/providers; production never loads test fixtures.

No frontend, repair service, inspection models, physical props, image measurements, redaction runtime, parcel lookup, voucher rules, or old `/api/housing` API remains. The Python package is `roomwise`, not `clearpass`. Historical source and private records were moved outside this project before removal.

## Service responsibilities

| Component | Responsibility | Does not own |
|---|---|---|
| `CatalogRepository` | Reviewed offers, source metadata, version history | Private student schedules or provider calls |
| `CampusRepository` | Supported campus and verified building IDs | Geocoding guesses |
| `EvidenceRepository` | Public source locators and review scope | Full-page or unlicensed review republication |
| `ComparisonService` | Monetary/room constraints, route coverage, limiting commitment | AI-generated prices or ranking by demographics |
| `RoutingAdapter` | Explicit supported/unavailable/unsupported route results | Silently converting straight-line distance to a walk |
| Gemma adapter + explanation service | Runtime boundary, bounded read tools, schema/citation validation | Writing catalog amounts or deterministic fit results |
| Guide service | Stable evidence-linked questions and user-owned progress | Legal conclusions, invented reviews or auto-completed tasks |
| `WorkspaceStore` | Editable revisions, comparison snapshots, immutable/idempotent briefs | Multi-user identity or cloud database behavior |

## Contract decisions

- All endpoints are under `/api/v1`; `/openapi.json` and `contracts/v1.openapi.json` describe the interface.
- Unknown price basis is represented as `unknown`; amount may be null. This is an intentional extension to the PRD's two known basis values, so absent facts are not fabricated.
- `route_date` is required separately from housing dates. It represents the explicit date to evaluate; requests on a nonmatching commitment weekday report unsupported coverage for that commitment. Evaluating a whole representative week is future adapter/service work.
- The API's `monthly_budget_per_person` is actually monthly. Contractual installments are not declared comparable to that budget without additional evidence. The base installment remains available as a labeled amount.
- Monetary amounts serialize as decimal strings. Optional housing dates must be supplied together; otherwise the stay remains unresolved.
- `input_revision` is returned with calculations. Reusing a comparison with another revision is rejected. Workspaces also reject stale writes. A changed catalog invalidates new AI explanation requests for an old comparison.
- Brief content comes from a persisted comparison snapshot. It cannot be supplied by a client as an authoritative price calculation. Checklist notes/status remain user-authored content.
- Error envelope: `status`, `request_id`, `error.code`, `error.message`, `error.retryable`. Validation errors do not echo raw submitted schedules. The HTTP response header includes `X-Request-ID` on normal responses.
- Generated examples under `contracts/fixtures/` are labeled fixtures and are never exposed as live route/model results.

## Persistence

Local adapter files are created under `ROOMWISE_DATA_DIR` (default `var/`):

- `catalog.sqlite3`: catalog, sources, append-only source versions.
- `workspaces.sqlite3`: versioned editable workspaces, immutable comparison records, frozen briefs.

No previous ClearPass database is opened or silently migrated. Corrected reviewed seed data initializes a fresh catalog. The previous private records remain in the external archive. Catalog corrections use a transaction and reject unexpected prices, unsupported quotes and newer reviews. Running a correction twice makes no duplicate change.

This is a single-user local adapter. Without a token, non-loopback clients are rejected. A configured bearer token protects the entire operator instance; it does not implement per-student ownership. CORS is disabled unless explicit origins are configured. Cloud Run, Firestore, Secret Manager and Cloud Storage are unimplemented deployment options, not active dependencies.

Deletion/retention policy for the local prototype: the owner controls the local data directory and external archive. There is no public multi-user deletion/retention service. Do not place student records on a shared server until ownership, deletion and retention controls exist.

## What runs versus what is still a boundary

Implemented: corrected housing catalog/evidence API, input validation, deterministic comparisons, coverage aggregation, revision checks, local workspaces, frozen JSON briefs, transactional price correction, deterministic checklist/progress, structured errors, API token/local-access boundary, generated OpenAPI and mock fixtures.

Official VT building locations are now imported: 350 named existing buildings with stable numbers and source queries. These establish building locations, not classroom access or verified entrances. Not implemented: a building-to-building routing provider; actual Gemma inference; token/time/concurrency controls for a live paid runtime; licensed reviews; Places or Gemini grounding; cloud persistence or deployment. Their absence is explicit in health/status responses. There is no automated source refresh endpoint or pricing publication by AI.

The retained BT GTFS adapter is narrowly useful for supported historical campus transit-center examples. It is not wired in as a classroom route provider because it does not include a complete class-building journey. Its outside-feed refusal remains tested.

The Gemma module provides a protocol, a bounded read-only evidence-tool boundary and schema/citation validation. It is not a successful inference integration. `ROOMWISE_EXTERNAL_ENABLED=false` disables even an injected external runtime through the HTTP layer. No expensive provider is contacted by this build.

## Next backend implementation order

1. Agree on the exported schemas with the frontend; add contract tests for any proposed changes.
2. Maintain the imported source-backed VT building locations and review entrances/classroom access separately.
3. Implement a real routing adapter with provider terms, date support, scope, permitted caching, timeout and quota behavior. Test two commitments with partial support.
4. Integrate a genuine Gemma runtime, enforce limits/retries/idempotency, and validate a recorded real explanation. Keep factual calculations in the domain/service layer.
5. Add ownership-aware cloud persistence and deployment only when needed; the local SQLite adapter is not a scalable multi-user claim.
6. Add authorized reviews and optional grounding after P0 evidence integrity is proven. Keep DormToDoor on the same comparison/catalog objects.

P2 vision, lease scanning, second-campus support and 3D have no implementation stubs in this backend.

## Local review collection added after restructuring

`adapters/offcampusreview.py` parses only public page JSON records and follows public discovery links under robots rules. `repositories/reviews.py` stores deduplicated review records and provenance in a separate, ignored research SQLite database. The CLI collection/supplement commands do not require account credentials and do not activate a public review API or inference use.

Review content is labeled subjective/unverified and reuse permission is not established. Listing snippets have a distinct text scope and cannot overwrite a full review. Email/author/account/address fields are not retained in structured columns; the original review text itself is not automatically de-identified. Authorized-use review querying, property matching and privacy/retention handling are still separate work. See `BACKLOG.md`.
