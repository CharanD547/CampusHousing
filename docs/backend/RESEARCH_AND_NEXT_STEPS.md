# Backend research and next steps

Checked October 24, 2026. This records public-source research and local verification, not a claim that every integration is built.

## Collected and stored

| Dataset | Result | Local storage | Operational use |
|---|---|---|---|
| OffCampusReview | 720 distinct reviews, 30 schools; 67 VT; 676 written, 44 rating-only | `var/offcampusreview.sqlite3` | Local research only; public/model use disabled |
| Official VT buildings | 350 named existing buildings with unambiguous building numbers, filtered from 700 source features | `data/campuses.json`, `var/public-data.sqlite3` table `buildings` | Building endpoint and real comparison destination validation |
| Blacksburg Transit | 297 stops, 24 routes, 4,067 trips, 81,780 stop times | `data/bt-gtfs.zip`; stops/routes also in `var/public-data.sqlite3` | Schedule evidence only; not a complete classroom routing engine |
| Additional housing evidence | Five observations covering rent ranges, specific-plan pricing and fees | `data/housing-research-observations.json`; SQLite `research_observations` | Research separated from published offer prices |
| Review subject candidates | 25 VT reviews across four catalog property aliases | Review database `property_match_candidates` | All marked `needs_scope_verification`; no automatic approved property mapping |

The GIS import uses the [official VT Buildings layer](https://arcgis-central.gis.vt.edu/arcgis/rest/services/facilities/BasemapWithBuildings/FeatureServer/1). The [Facilities GIS description](https://www.facilities.vt.edu/operations/gis.html) distinguishes public maps from employee-only resources. Only the public layer was queried. Records retain exact source queries and retrieval times. Names, numbers and coordinates are source-backed; this does not establish classroom availability, entrances, accessible paths, or indoor travel. Non-academic buildings can appear. Null numbers, planned/demolished records, ambiguous duplicate numbers and locations outside the declared central Blacksburg bounds are excluded. Source access does not itself establish a general redistribution license.

The refreshed [official BT feed](https://www.bt4uclassic.org/gtfs/google_transit.zip) declares **October 1–31, 2026**, version FY27 Blacksburg 1.8A. These are timetable dates, not a 2027 service guarantee. Official rider information is available from [Blacksburg Transit](https://ridebt.org/routes-schedules/plan-a-trip). November and 2027 dates must remain unsupported until corresponding feed/provider evidence exists.

Reports: `var/vt-public-data.collection.json`, `var/remaining-research.collection.json`, `var/offcampusreview.collection.json`. Raw building response and content hashes permit checking the import. Research tables are excluded from version control and containers through `var/`.

## Pricing findings that still need reconciliation

- [Foxridge public floor plans](https://foxridgeliving.securecafe.com/onlineleasing/foxridge-apartments-0/floorplans.aspx) expose plan-specific ranges. Grove includes inconsistent per-person promotional text alongside its rent range. Do not turn a range minimum into a guaranteed available whole-unit offer. The [fee guide](https://www.foxridgeliving.com/gridmedia/img/fees.pdf) establishes additional recurring charges and screening-dependent deposits; deposits differ from the plan page. Resolve the selected unit and term before publishing a correction.
- [Windsor Hills](https://www.windsorhillsapts.com/floorplans/) provides a [fee guide](https://www.windsorhillsapts.com/gridmedia/img/fees.pdf), but the linked leasing inventory redirects to sign-in. No account was created and no login was attempted. Base rent remains unknown.
- [Terrace View pricing](https://terraceviewblacksburg.com/pricing) embeds plan-specific leasing totals; its [fee disclosure](https://terraceviewblacksburg.com/fees) uses installment billing for several charges. A specific 2027–28 plan example is captured, but base rent, total leasing price and fees need reconciliation to prevent double counting. Generic one-/two-/four-bedroom catalog placeholders are not exact plan matches.
- The existing reviewed Alight, Union and Mill amounts remain the live catalog. This research does not certify current unit availability or resolve every mandatory cost.

Automated snapshot retrieval succeeded for Terrace View fees and OCR terms. The conservative source adapter could not verify robots access for Foxridge's leasing host, Terrace View's snippet host and the VT graduate housing page. Browser/search-readable findings retain their links, but those hosts were not forced through the scraper. PDF disclosures were read separately. The source-access report distinguishes these methods and failures.

## Routing: implementation choice remains

**Open data route:** [OpenTripPlanner](https://docs.opentripplanner.org/en/latest/Basic-Tutorial/) builds a routing graph from GTFS plus OpenStreetMap street data and supports arrival-constrained transit journeys with walking. It requires a real graph build and service, then a Roomwise adapter and tested itinerary extraction. The [Virginia Geofabrik extract](https://download.geofabrik.de/north-america/us/virginia.html) is a downloadable source; a bounded Blacksburg extract is preferable to carrying statewide data. OSM [attribution and ODbL obligations](https://www.openstreetmap.org/copyright) apply. No graph/model was downloaded or claimed as working during this research.

**Google route:** [Routes API](https://developers.google.com/maps/documentation/routes/compute-route-over) is a credentialed alternative. [Transit requests](https://developers.google.com/maps/documentation/routes/transit-route) accept arrival time, with the documented past/future window; that window does not prove a particular local trip exists. Billing and a restricted key are required according to [usage documentation](https://developers.google.com/maps/documentation/routes/usage-and-billing). [Storage and attribution policy](https://developers.google.com/maps/documentation/routes/policies) must be reconciled with immutable comparison/brief snapshots before persisting provider results. Do not blindly add a Google response cache to the current SQLite design.

For either option: enforce full context (origin/destination, date, timezone, arrival buffer, mode); distinguish unsupported from no-route; validate walking access and campus last mile; report scheduled versus live service; enforce timeout and request ceilings. Deduplicate identical property origins across offers within the permitted scope. Never use a driving profile as a walking estimate. Test two actual commitments, an outside-feed date and a partial failure. Existing comparison tests verify missing routes remain unavailable.

## Gemma: supported access identified, inference still absent

Google's [hosted Gemma guide](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api) currently documents `gemma-4-31b-it` and `gemma-4-26b-a4b-it`, requiring an AI Studio API key. Its [function-calling guide](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4) describes the application executing bounded tools. No Google/Gemini/Maps API credential was present in this process environment; no account access, model inference or quota was proven.

Implement the real runtime behind the existing protocol, with model ID verification, bounded evidence retrieval, no arbitrary URL/SQL execution, time/output/concurrency/request limits, retry/idempotency and an owner disable switch. Capture a real successful explanation, invalid-citation rejection and unsupported-question behavior. Keep deterministic prices and constraints authoritative. Do not feed the review corpus to a model until its use scope is established.

## Review use and property matching

[OCR terms](https://www.offcampusreview.com/terms-conditions) revisited today display a September 1, 2026 update. Contributors retain ownership and grant rights to OCR; a Roomwise republication/model-use license was not established. This is a factual reading of the displayed terms, not a legal clearance. Robots permission is separate from reuse rights.

The candidate mappings use school plus explicitly listed subject aliases: Foxridge 12, Alight 6, Union 4, Terrace View 3. They do not prove the precise property/unit identity, especially Alight East versus West. Windsor Hills and The Mill have no approved matches. Next: establish allowed use, review identities and date/sample scope, remove sensitive text as appropriate, implement source-edit/removal propagation and deletion/retention rules, then expose evidence-scoped queries. Never treat reported safety experiences as an official safety score.

## Hosting and shared access

[Cloud Run's container contract](https://docs.cloud.google.com/run/docs/container-contract#filesystem) describes ephemeral container filesystem storage. Current local SQLite files therefore cannot serve as the durable shared database unchanged. Migrate the repository boundary to managed storage, e.g. Firestore, with transactions, ownership checks and immutable snapshots; configure [Secret Manager injection](https://docs.cloud.google.com/run/docs/configuring/services/secrets). Server-side Firestore clients [bypass client Security Rules](https://docs.cloud.google.com/firestore/native/docs/security/get-started), so backend owner checks and service-account IAM remain necessary.

Before sharing: authenticated user ownership, retention/deletion/recovery, provider request caps, explicit CORS, durable persistence, deployment health checks and a clean hosted integration run. The current token grants access to one operator instance and does not isolate students. No cloud deployment or billing resource was created.

## Exact next build order

1. Choose and implement the routing service; the building destination data prerequisite is now available.
2. Configure and implement genuine Gemma inference with bounded tools and recorded validation.
3. Run the complete real flow: two commitments → comparison → explanation → checklist → immutable brief. Current partial comparisons and deterministic checklist already work.
4. Reconcile the newly found specific housing plans, charges and deposits; apply reviewed transactions with supporting source records.
5. Resolve review reuse and exact property scope before review-backed summaries.
6. Add user ownership and durable cloud storage before a shared deployment.

Scraping more websites cannot substitute for these implementation and verification steps. Optional Places/grounded neighborhood answers, representative-week routing, second campuses and lease/image features remain behind the P0 flow.
