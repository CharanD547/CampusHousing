# Roomwise

Student housing decisions for Virginia Tech, combining the supplied frontend with a same-origin FastAPI backend. Explore source-reviewed housing offers, set preferences and class commitments, compare up to three offers, track the DormToDoor checklist, and save immutable server-owned decision briefs.

## Run

Python 3.11+ is required. The current workspace already has a development environment. For a fresh checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev-lock.txt
.\.venv\Scripts\python.exe tools/build_frontend.py
.\.venv\Scripts\python.exe -m uvicorn roomwise.main:app --app-dir src --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001/ for Roomwise, http://127.0.0.1:8001/docs for API documentation, and `/api/v1/health` for provider readiness. Loopback is the default for this single-user prototype. The current requested LAN development run listens on all IPv4 interfaces with operator authentication; see [LAN access and restart instructions](docs/LAN_DEVELOPMENT.md). The Python package is now `roomwise`; the existing workspace folder name is unchanged. Database files and collected research remain intact.

## Connected behavior

- The supplied `CampusHousing-main/src/` design is served at `/`. Rebuild after changing the shell or CSS. JavaScript and the illustrative hero asset are served under `/assets/`. No Node dependencies or frontend build installation are required.
- The browser loads 18 offer/category records across six properties and 350 official VT GIS building locations. Fixture properties and fixture commute calculations were removed. Building points are not verified entrances or classroom inventories.
- Preferences, dates, modes and classes drive server comparisons. Whole-unit splits are explicit scenarios; installments remain distinct from calendar-month rent. Empty schedules permit browsing but cannot establish commute fit.
- Shortlists, notes, questions, example-schedule provenance, checklist progress and saved brief references sync to SQLite. Browser storage provides a draft cache; sync failures and revision conflicts are visible. A conflict can be resolved by first backing up the local draft and loading the server copy.
- DormToDoor requests server-generated checklist items. Regeneration preserves status and notes for stable items. User items remain user-owned and do not become reviewed evidence.
- Briefs freeze the server comparison, original catalog/building records, selected offers, questions and checklist. Refresh restores them from the backend. Later catalog edits do not alter stored snapshots.
- Property details show original evidence links and additional fee/range research, excluded from comparison totals until reconciled to an exact offer.

## Current limits

The [assistant](http://127.0.0.1:8001/#assistant) now works without credentials as a clearly labeled local research helper. It uses the saved comparison and authored rules; it is not a Gemma/Gemini model run. Hosted/custom-model transports and a separate Gemma LoRA preparation/training/serving/evaluation workflow are available. See [assistant and training instructions](docs/AI_AND_TRAINING.md). No model has been trained or loaded yet.

Google Maps now renders live property/building markers, and property details offer on-demand nearby essentials through server-side Google Places. A schedule-aware Google Routes adapter supports walk/bike/drive/transit requests, explicit per-class buffers and single-date or representative-week scope. A separate Routes credential is now validated and enabled; live walking/transit journeys were verified in Chrome. Request budgets can still leave partial coverage. Genuine Gemma inference also remains unconfigured. Missing results stay unavailable. The imported BT feed covers October 1–31, 2026; it is not a complete classroom routing engine or a future service guarantee. The Google Map and its coordinate fallback show approximate destinations; no travel-time shading is invented. Google provider content remains transient and is excluded from saved briefs and training. Asking figures are dated evidence, not guaranteed availability or complete costs.

The isolated review database contains 720 distinct reviews, including 67 VT records. No public review text or model ingestion is enabled until reuse scope and exact property matching are established. Five additional housing observations and tentative review-subject mappings are stored separately from authoritative prices.

Default mode remains one local operator. Optional `ROOMWISE_ACCOUNTS_REQUIRED=true` enables local accounts with salted password hashes, expiring HttpOnly sessions and ownership checks for workspaces, comparisons, briefs and recovery. Existing operator records remain separate. This is not managed cloud identity, email recovery or a production hosting claim. Cloud persistence/deployment and cross-device operation remain unverified.

## Configuration and storage

`.env.example` documents application, AI and Google Maps settings. The backend reads the workspace `.env` at startup; process environment variables take precedence. Both Git and Docker exclude the real `.env`. Enabling external operations alone does not configure a provider. A configured application access token is entered in the browser connection form and held in session storage; API requests use its bearer header. Private Places/Routes/model keys stay server-side and must not be entered in that browser access-token form. The designated Maps JavaScript key is intentionally returned to the browser SDK. Explicit Maps/Places/Routes switches control integration; the shared daily web-service attempt limit defaults to 40 and includes failures. Browser map usage is outside that server cap. Verify account-level key restrictions and quotas separately.

Default local storage under ignored `var/`:

| File | Contents |
|---|---|
| `catalog.sqlite3` | Reviewed catalog, evidence and source versions |
| `workspaces.sqlite3` | Revision-checked workspaces, comparisons and immutable briefs |
| `offcampusreview.sqlite3` | Isolated public-review research collection |
| `public-data.sqlite3` | Buildings, transit stops/routes and research observations |

`var/frontend-input-original.zip` preserves the supplied frontend before integration. The earlier backend purge archive remains outside the workspace; see [purge record](docs/backend/PURGE.md).

## Verification and maintenance

```powershell
.\.venv\Scripts\python.exe -m pytest -q
node --test tests/frontend_adapter.test.cjs
.\.venv\Scripts\python.exe tools/backend/export_contracts.py
.\.venv\Scripts\python.exe tools/backend/apply_price_review.py --data-dir var
.\.venv\Scripts\python.exe tools/backend/collect_vt_public_data.py
.\.venv\Scripts\python.exe tools/backend/collect_offcampusreview.py
.\.venv\Scripts\python.exe tools/backend/supplement_offcampusreview.py
.\.venv\Scripts\python.exe tools/backend/research_remaining.py
```

Node is needed only for the optional adapter checks. Browser verification is recorded in [integration notes](docs/INTEGRATION.md). OpenAPI is generated from the application schemas. The nonroot Dockerfile and loopback-only Compose recipe package the frontend/backend with a persistent volume and a health check. Docker and gcloud are unavailable here, so no container build or cloud deployment is claimed. A fresh production-dependency virtual environment was installed and exercised over HTTP with isolated databases. See [completion report](docs/COMPLETION_REPORT.md).

[Backend PRD](docs/backend/PRD.md) · [architecture](docs/backend/ARCHITECTURE.md) · [remaining work](docs/backend/BACKLOG.md) · [research](docs/backend/RESEARCH_AND_NEXT_STEPS.md) · [reviews](docs/backend/REVIEW_COLLECTION.md).

MIT application license; source content, data and model/provider terms are separate. Original contributor notices remain intact.

## Data recovery and operational checks

The Data page exports individual records and provides recoverable trash/restore for workspaces and briefs. Trash is retained until a documented operator purge; it is not permanent erasure of related snapshots, drafts, exports or backups. Optional accounts scope these actions to their owner. Default operator mode can see all local operator records.

```powershell
.\.venv\Scripts\python.exe tools/backend/audit_readiness.py --report var/readiness-audit.json
.\.venv\Scripts\python.exe tools/backend/backup.py backup var var/backups/NEW-NAME
.\.venv\Scripts\python.exe tools/backend/backup.py restore var/backups/NEW-NAME var/NEW-RESTORE-DIRECTORY
.\.venv\Scripts\python.exe tools/backend/verify_release.py --python .venv/Scripts/python.exe --report var/clean-install-verification.json
```

Backups use SQLite snapshots, SHA-256 manifests and integrity checks. Restore requires a new destination, verifies every database before creating it, and never overwrites running storage. Individual databases are consistent; a live multi-database backup is not one global transaction. Credentials, browser drafts and model weights are excluded. The completed seven-database restore drill is in ignored `var/recovery-drill-20261024/`. See [operations](docs/OPERATIONS.md).
