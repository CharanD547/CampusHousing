# Roomwise completion and verification

October 24, 2026. Local implementation is running at [Roomwise](http://127.0.0.1:8001/). This report distinguishes completed work from external release gates.

## Delivered in this run

- Validated the supplied Maps JavaScript and Places credentials. Maps rendered in Chrome; on-demand nearby cafe search returned real results. Grocery search correctly displayed a valid empty result. Private Places credentials do not reach the browser.
- Integrated live Google Maps markers, selection, fallback overview, instance reuse, accessible marker events, source attribution, nearby essentials and provider disclosures.
- Implemented Google Routes requests with mode/date/buffer handling, daily caps, per-comparison attempt/time budgets, partial failure and transient retention. Routes is disabled: the available Places credential was denied by Routes, and no separate Routes credential is configured.
- Added representative-week analysis, with each dated meeting counted separately, plus matching frontend/frozen-brief handling.
- Added optional local accounts and server ownership checks, separate browser drafts, sign-in/out, salted password hashes, expiring sessions and bounded login attempts. Default operator mode remains unchanged.
- Added Data export, recoverable trash/restore, database backup/restore tooling, route-template operational logs, public privacy/terms and a readiness audit.
- Rechecked The Mill's three whole-apartment prices and installment basis against its official pages; refreshed seed and running database through the audited transaction. Alight/Union corrections remain intact. Nine numeric asking prices are reviewed October 24. Nine other categories remain unknown; additional ranges/fees remain separate observations.
- Updated generated OpenAPI, production dependencies/timezone data, nonroot Docker/Compose recipes and operational documentation.

## Evidence

| Check | Result |
|---|---|
| Python suite | 52 passed; one upstream Starlette/httpx test-client deprecation warning |
| Node presentation checks | 5 passed, including weekly partial coverage and LAN HTTP UUID fallback |
| Dependency consistency | Development and fresh production environments passed `pip check` |
| Fresh production install | Locked dependencies installed in a new virtual environment |
| Fresh HTTP instance | Public shell/privacy, bearer rejection, 18 offers, 350 buildings, weekly comparison, workspace, checklist, brief reload, local helper and export/trash/restore passed |
| Storage integrity/recovery | Seven SQLite databases passed integrity checks; all seven backed up and restored into a new directory |
| Provider boundary tests | Buffer/timezone, modes, request deduplication, denied/out-of-window routes, quota exhaustion, secret exclusion and no persistent Google route content passed |
| Account isolation | Two accounts could not read/write another's records; sign-in/out, export/trash ownership and origin rejection passed |
| Browser | Desktop Chrome map, property pricing, nearby search, weekly controls and Data view checked; final observations are in integration notes |
| Gemma preflight | 192 authored training / 24 validation / 24 test examples checked; zero imported reviews; no weights/training/inference run |

Machine-readable local evidence: `var/google-key-validation.json`, `var/clean-install-verification.json`, `var/readiness-audit.json`, `var/training-preflight-final.json`, and the backup manifest. These ignored files contain local operational evidence, not credentials to publish.

## Still blocked or intentionally incomplete

These gaps include credentials, source permissions, unfinished code and unperformed tests. Supplying API keys alone will not complete all of them. The following describes what must happen; it does not claim that these steps have run.

### 1. Live commute estimates and useful weekly coverage

**Status update:** a newly supplied Routes credential passed live validation and Routes is enabled. The existing localhost Chrome flow produced live journeys to both selected class buildings. Credential access is no longer blocked; coverage scheduling/budget limitations below still apply. Provider durations are not stored in this report.

**Earlier state:** Maps and Places worked while the original Places credential was denied by Routes. A separate Routes credential is now validated, configured and enabled. The earlier denial did not establish the precise account setting responsible.

**Owner/account inputs needed**

- A Google Cloud project with billing and Routes API enabled, plus a backend credential authorized for Compute Routes. A separate backend Routes key is the intended configuration. Browser Maps access does not establish Routes authorization.
- API/application restrictions appropriate to the backend deployment. Browser referrer restrictions and backend source-IP restrictions serve different clients; do not remove all restrictions to make a test pass.
- Project quotas and an agreed spending limit. Application attempt caps are separate from provider billing controls; browser Maps usage is outside the server web-service cap.
- Set `ROOMWISE_ROUTES_API_KEY` in protected local configuration or hosted secret injection. Enable `ROOMWISE_ROUTES_ENABLED=true` for an intentional live exercise and restart the backend. No Gemini API key is required for this adapter.

**Engineering and verification still needed**

- Exercise real walk, bike, drive and transit requests for official VT destinations, dates, arrival buffers and timezone/DST cases. Unsupported dates or modes must remain unavailable.
- Address the coverage budget: the adapter permits at most 12 network attempts per comparison and 40 combined Places/Routes attempts per day by default. Six properties × two destinations × two modes can need 24 distinct requests on one date; weekly meetings need more. A working key therefore still leaves partial results under current limits.
- Route shortlisted candidates first, request journeys on demand, or implement bounded incremental batches with progress and coverage counts. Raising limits requires a cost decision. Reuse identical property journeys where permitted.
- Retain limitations: driving excludes parking search; building points are not verified accessible entrances; static walk/bike/drive estimates do not establish future conditions. The October BT feed does not guarantee later service. A separate GTFS routing engine would require feed refresh, calendars, walking connections and transfer routing.
- Preserve attribution/retention rules. Google routes are currently excluded from saved comparisons, briefs and model context. Any future live-route model integration needs a separately reviewed data flow.

**Done when:** real requests cover at least two buildings and each enabled mode/date, partial-week and denied/quota cases work, selected candidates receive useful coverage, latency/request counts are measured, and prohibited provider content is not persisted.

References: [Routes setup](https://developers.google.com/maps/documentation/routes/get-api-key), [billing and quotas](https://developers.google.com/maps/documentation/routes/usage-and-billing), [Routes policies](https://developers.google.com/maps/documentation/routes/policies).

### 2. Genuine Gemma training, serving and product integration

**Current state:** the working assistant is `local_rules`, with no model ID. Model transports and LoRA preparation/training/serving/evaluation scripts exist. No weights, trained adapter, actual model answers or demonstrated improvement exist. The 240 authored examples split into 192 train / 24 validation / 24 test; shared templates make this a pipeline starter rather than an independent quality benchmark.

**Access and environment needed**

- Authorized `google/gemma-3-1b-it` weights, with applicable model terms accepted by the account holder. For gated Hugging Face access, use a read-scoped token with permission for the model, or supply already-authorized local weights. A Gemini API key does not replace this access.
- A separate, compatible CUDA-enabled Torch/Transformers/PEFT/Datasets/Accelerate environment, with a tested dependency lock. Optional requirements currently contain starter ranges. Keep training dependencies out of the lean API image.
- Validate driver/GPU support, BF16, peak memory and actual speed. Approximately 24 GB VRAM was observed, but a successful training run has not established compatibility.

**Dataset and model work**

1. Review authored labels and add independently written evaluation cases for billing, missing charges, contradictory evidence, route coverage, unsupported questions and prompt injection.
2. Use only data with an established training-use basis. Imported resident reviews are not currently approved training data. If permissioned real data is added, minimize personal information, deduplicate and split by property/source/time.
3. Evaluate the untuned base model. Run LoRA training; verify masking/truncation; record base revision, dataset hashes, dependencies, settings, memory and losses; save adapter/tokenizer artifacts.
4. Compare base and adapter on the same genuinely held-out cases. Check factual support, financial/billing correctness, uncertainty, citation support, JSON validity and latency. Lower validation loss or a valid citation ID alone does not establish answer quality.
5. Retrieve current prices and availability at inference time. Train evidence-use behavior rather than memorizing volatile asking prices.

**Serving and application work**

- Start and verify the local model server using authorized weights and the adapter. Configure `ROOMWISE_AI_PROVIDER=openai_compatible`, the actual model alias, the local `/v1` URL and `ROOMWISE_EXTERNAL_ENABLED=true`. The local model route needs no Gemini API key.
- Test real generations through `/api/v1/assistant/messages` and the browser, including invalid outputs, unsupported citations, timeouts and quotas.
- Complete the separate explanation integration if it is part of the demonstration: `/api/v1/ai/explain` still defaults to `UnconfiguredGemmaRuntime`. Configuring the chat transport does not automatically wire this endpoint. It needs a runtime adapter, bounded evidence access, quota handling and verified responses.
- The evidence-tool boundary is not a verified autonomous tool-calling loop. Implement orchestration only if required. Nearby Places content remains excluded from saved model context; review-derived answers also depend on item 4.
- Hosted inference additionally needs compute/hosting selection, private artifact storage, network access control, startup/concurrency limits and a spending budget.

**Done when:** a reproducible training report and saved adapter exist, held-out generations have been reviewed against the base model, and Roomwise produces real model-backed answers with an actual model identity. A custom-trained-model claim or improvement claim requires this evidence. Hackathon eligibility remains a separate organizer-rules check.

A hosted Gemini key could support a separately tested Gemini assistant, but would not complete custom Gemma training. Google Search grounding is optional and currently unimplemented; adding it would require provider support, citations and separate data/cost verification.

References: [project model workflow](AI_AND_TRAINING.md), [Gemma access](https://ai.google.dev/gemma/docs/integrations/langchain), [Gemma tuning](https://ai.google.dev/gemma/docs/tune).

### 3. Exact pricing, mandatory costs and availability

See the [property-by-property field audit and fee implementation gaps](DATA_GAPS.md#3-complete-pricing-and-availability) for exact missing records, known separate observations, operator quote requirements and backend work.

**Current state:** nine numeric asking prices were reviewed October 24. Nine entries remain unresolved: three Foxridge categories, three Terrace View categories and three Windsor Hills categories. Additional ranges, fees and a particular Terrace offer do not automatically describe those generic records.

**Required evidence for each comparable offer**

- Exact property, unit/floor plan, bedroom scope, occupancy assumptions and whether the quote describes available inventory or general advertising.
- Amount/currency, whole-unit versus per-person basis, calendar-month versus installment frequency, payment count, lease dates and applicable term.
- Mandatory recurring fees, included/usage-based utilities, optional extras, one-time charges and refundable deposits, including screening-dependent ranges and the charging basis.
- Source URL, retrieval/review date and field-level evidence. Conflicting operator pages need reconciliation rather than selection of the lowest figure.
- Availability and quote validity, or an explicit unknown. A fresh asking-price review is not an inventory guarantee.

**How to finish:** inspect accessible official disclosures; obtain an operator-provided quote or authorized feed/export where public pages are incomplete. Contacting properties would require explicit authorization to send messages. Preserve unknowns when exact matching is not possible. Apply reviewed updates transactionally to seed and live storage, append provenance, retain historical briefs, and establish a source-refresh/change-review workflow.

**Done when:** every record advertised as a comparable priced offer has exact supporting evidence; unknown charges and stale data remain visible; billing arithmetic is correct; live data updates without changing historical briefs. Generic unresolved categories may remain research leads. No Google API key can supply missing operator evidence by itself.

### 4. Permissioned reviews and review-based summaries

See the [review corpus, mapping, permissions and AI implementation audit](DATA_GAPS.md#4-resident-reviews-and-review-based-ai) for actual counts and the detailed completion checklist.

**Current state:** 720 public research records, including 67 VT records, are isolated from product/model use. Reuse permission is unestablished. Twenty-five tentative property matches need review, including the Alight East/West distinction. Collection alone does not establish redistribution or training rights.

**Needed before enabling**

- Establish allowed retention, display, excerpts, summaries, embeddings, model processing/training and derivative-artifact distribution for the intended use. Applicable licensing, platform authorization or an appropriately authorized original contributor dataset may provide a basis; one permission must not be assumed to cover every use.
- Record source/property/school/unit scope, review period, update dates, allowed uses, attribution and removal obligations. Minimize unnecessary personal information.
- Review exact property matches, deduplicate, distinguish rating-only from full-text records, and preserve the difference between historical opinions and current evidence.
- Implement permission-aware retrieval, attribution, date/sample-size caveats, source updates/removals and propagation into indexes, datasets and derived products. Define what happens to published summaries/adapters when source material must be removed.
- For model use, create reviewed aspect/uncertainty labels and independent evaluation; test invented consensus, unsupported claims and instructions embedded in source text.

**Done when:** every included record has documented allowed use and reviewed matching, citations/coverage are clear, removal/update tests pass, and summaries are supported by permitted evidence. Ambiguous/unlicensed material remains excluded. Opinions must not become official safety scores or guarantees of current conditions.

Places API access is not a blanket review dataset or training license; it has separate storage, attribution and use rules. See [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies). An explicitly permissioned original feedback dataset is an alternative, with its own use/retention scope.

### 5. Cloud persistence, account lifecycle and production readiness

**Current state:** local SQLite, optional owner isolation and recovery work. Docker/Compose recipes exist; no container build or cloud deployment ran. Docker/gcloud were unavailable locally. An authorized CI/cloud build environment could provide an alternative to local CLI installation.

**Hosting and persistence work**

- Choose a cloud project/account, billing budget, region, deployment identity and runtime identity. Provision the selected services and grant access only to their required database/secrets/artifacts.
- Select and implement durable repositories. For Cloud Run, migrate to a managed database such as Firestore or PostgreSQL instead of relying on container-local SQLite. Preserve ownership, optimistic revisions, immutable briefs, source history, idempotency and atomic quota accounting. Naming a database does not implement migration.
- Cloud Run's ordinary writable filesystem does not persist after instance termination; autoscaled instances would also have separate SQLite quota/session files. Shared operational state must be durable. See the [Cloud Run runtime contract](https://docs.cloud.google.com/run/docs/container-contract).
- Inject protected secrets and use service identity where supported. Keep reviews, exports, backups and model artifacts private with defined storage lifecycles.
- Build/scan the Linux image; verify nonroot operation, writable storage, startup and health checks. Configure the service container port to 8001 or make startup honor its configured port. Test failed deployments and rollback.
- Define hosted access: the shared operator token is not a public student authentication system. Configure TLS, secure cookies and trusted origin/proxy handling without exposing an operator secret to public clients.

**Identity, retention and reliability work**

- Choose and implement account verification/recovery, session revocation, account export/deletion and abuse controls. A managed identity provider is one possible implementation. Current local accounts lack email verification, password recovery and account deletion.
- Set concrete retention periods for workspaces, comparisons, briefs, assistant responses, reviews, sessions, logs and backups. Implement owner-authorized purge and an explicit recovery period. Current trash retains records indefinitely.
- Include related immutable snapshots/derived data and backup expiration in deletion behavior. Disclose browser drafts and downloaded exports outside server control. Immutability must not silently require indefinite retention of private records.
- Make quotas, rate limits and concurrency correct across instances. Add privacy-preserving error/latency/provider-denial/cost/storage monitoring and alerts.
- Replace remaining generic nested cost/provider dictionaries with explicit schemas where required, version the contract and test malformed outputs. Complete mobile/accessibility, hosted multi-user/concurrency, outage, migration and recovery tests. Existing local tests do not prove these outcomes.

**Done when:** a real HTTPS deployment isolates two independent users, survives restart/redeploy without losing data, enforces shared quotas, keeps secrets private, passes backup/restore and account-lifecycle/deletion drills, and has useful monitoring plus a tested rollback.

### Recommended order and required inputs

| Priority | Work | Owner input | Engineering work |
|---|---|---|---|
| 1 | Live routes | Authorized Routes credential and quotas/budget | Coverage scheduling and real mode/date/UI tests |
| 2 | Real Gemma | Authorized weights/access and chosen compute | Runtime lock, baseline, training, evaluation, serving and endpoint wiring |
| 3 | Pricing completeness | Exact operator evidence or authorized feed/quote | Reconciliation, audited updates and freshness workflow |
| 4 | Hosted pilot | Cloud identity/project, database/auth choices and budget | Durable repositories, TLS/auth, shared quotas, deletion and deployment tests |
| 5 | Review enrichment | Established rights and reviewed property matches | Permission-aware retrieval, attribution, removal propagation and evaluated summaries |

Routes and Gemma are the main missing pieces for the intended real-provider/custom-model demonstration. Explicit unknown prices can remain in a local research demo. Shared deployment needs the hosting/identity gates. Review enrichment can stay disabled until its separate permissions and quality gates are satisfied.

No deployments, provider permission changes, key-restriction changes, model-license acceptance or permanent data purge were performed. These are concrete remaining dependencies, not completed features hidden behind fallback UI.

Official pricing evidence: [The Mill floor plans](https://www.blacksburgmill.com/floor-plans/) and [installment FAQ](https://www.blacksburgmill.com/faq/). Provider integration follows the [Google Places attribution/retention guidance](https://developers.google.com/maps/documentation/places/web-service/policies).
