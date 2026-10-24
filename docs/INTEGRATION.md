# Roomwise integration and verification

## API-free assistant follow-up

The assistant navigation and local research helper were added and tested in Chrome after the initial integration below. It answered an installment question without a model run and used selected-offer comparison facts for cost questions. Every local answer identifies its rule-based origin. Model operations remain disabled; no external inference API was contacted. The current suite passes **40 Python tests and 3 Node adapter tests**. Dataset preparation and evaluation preflight ran without model inference; no trained Gemma is claimed. See [AI and training workflow](AI_AND_TRAINING.md).

October 24, 2026. The supplied frontend is now integrated with the backend and branded Roomwise. The Python package, ASGI entrypoint, metadata, environment variables, browser storage namespace, UI and maintained documentation use the new name. The workspace path is unchanged. Earlier immutable records and archived source content are not rewritten.

## User story

A student loads source-reviewed housing and official building locations, sets preferences and an example or personal schedule, shortlists offers, compares server results, tracks a backend-generated checklist, and saves a frozen server brief that survives a page reload.

## Verification

| Boundary | Result | Evidence |
|---|---|---|
| Browser renders | Passed in Chrome | Roomwise brand, 18 offers, actual catalog amounts and unavailable-provider labels; `var/roomwise-integrated.png` |
| Browser → API | Passed | Catalog, buildings, evidence, research, comparisons, checklist, workspace and brief requests returned 200 in server logs |
| API → data | Passed | SQLite workspace stored selected offer, two example commitments, October 26 route date, checklist progress and saved brief reference |
| Data → response | Passed | Server subtotals and partial coverage mapped into the supplied design; fixture routing and client-generated fit verdicts removed |
| Response → browser | Passed | Alight East displayed $835 per person per installment, 0 of 2 supported commitments; checklist remained in progress after input revisions |
| Frozen brief | Passed | Saved and reloaded the server brief with checklist progress visible. New comparisons capture building labels as well as catalog data |
| Real routing/Gemma | Not configured | Missing estimates and `ai_unavailable` remain explicit; no successful real-provider inference/routing is claimed |
| Browser errors | None observed in tested flow | Chrome error-log query returned an empty list |

Automated checks: **34 Python tests and 3 Node adapter tests passed**. JavaScript syntax checks passed. Python reports one upstream Starlette/httpx deprecation warning. OpenAPI was regenerated. No container build or cloud deployment was tested.

## Integration choices

- `/` serves the app; `/assets/` serves frontend source/assets; `/api/v1/` remains the backend contract; `/docs` exposes API documentation. All share port 8001.
- No frontend dependencies were added. `tools/build_frontend.py` builds the shell/CSS entrypoint with Python. JavaScript is served directly and the hero image remains illustrative.
- Canonical modes are `walk`, `transit`, `bike`, `drive`, replacing frontend-only `bus` and `car` names.
- Empty schedules permit browsing but return missing commute evidence. Zero classes never establishes commute fit.
- Comparisons capture original catalog and building records. The UI displays server fit states and subtotals; outdated results are hidden when inputs change.
- Browser drafts coexist with revision-checked workspaces. Edits during a save queue another save. Offline drafts remain cached; competing-tab conflicts pause sync and offer a recoverable local backup before loading the server copy.
- Checklists come from `/guide/checklist`, preserve stable-item progress and retain user items. Example schedules are marked through `is_example` and restored as samples.
- Briefs come from `/briefs`; client code cannot supply replacement prices or fit verdicts. Questions and checklist state are identified as user-supplied. Model output is not silently included.
- `/research/housing/{property_id}` exposes additional disclosure facts, links and limitations. These are excluded from totals until reconciled to the exact offer.

## Data and remaining work

The collected 350 GIS building locations, 297 transit stops, 24 routes and five housing observations supply the integration. Repeating the same-day full review crawl was unnecessary. The 720-review database is preserved and remains isolated from public/model use pending reuse scope and exact-property verification.

Next: real routing and genuine Gemma inference with limits and recorded provider verification; then exact offer/fee reconciliation and review-use controls. Multi-user authorization, durable managed storage and deployment remain separate release work. See [backend backlog](backend/BACKLOG.md). Existing databases were retained; `var/frontend-input-original.zip` preserves the frontend as supplied.


## Final completion run — October 24, 2026

- Desktop Chrome rendered the real Google Map and all six housing markers plus selected campus locations. Selecting Alight updated its selected card; the final retest confirmed all markers remained visible after the view refreshed. The initial marker lifecycle issue was fixed by rebuilding marker elements on the retained map instance. Final proof: `var/roomwise-final-map.png`.
- Alight East details displayed $835 per person per installment and a 12-payment base total, with missing required charges explicit. Nearby groceries produced a valid empty result; cafes returned actual Google Maps place links, including Coffee Lab and Halwa Bakery & Cafe. No review fields were requested.
- Schedule scope changed to representative week, advanced revision 3 to 4, saved to the backend and remained selected after reload. API tests additionally checked Monday/Wednesday/Friday occurrences and partial coverage without choosing one fastest trip for an entire week.
- Data displayed existing workspaces and immutable briefs with export/trash controls. Clicking Export JSON downloaded a valid `roomwise-record-v1` workspace JSON file to Downloads; the exported weekly scope was checked without printing private schedules or notes. Trash/restore and cross-account denial were verified against isolated test databases, not by deleting the user's existing records.
- A fresh production-only virtual environment passed the standalone HTTP smoke test with fresh databases: shell/privacy, bearer rejection, 18 offers, 350 buildings, three weekly meetings, workspace, checklist, immutable brief reload, local helper and export/trash/restore. No real provider calls were made by that isolated smoke test.
- Final Python suite: 51 passed, one upstream Starlette/httpx deprecation warning. Node presentation suite: four passed. Changed JavaScript files parsed successfully, both environments passed pip dependency checks, and 103 source/document/config files were checked for the actual supplied credential values without displaying them; no copies outside excluded local configuration were found.
- Seven databases passed integrity checks and a backup/restore drill. A later final backup including the source recheck and saved weekly workspace is at `var/backups/final-20261024-1644/manifest.json`. The recovery drill restores to a new directory and leaves active databases untouched.
- An older Maps marker API deprecation warning was observed and its event handler was updated to `gmp-click`; no application error was observed in the final browser flow. No mobile-browser, actual Gemma generation, live authorized Routes, container or cloud execution is claimed.

Current implementation and external release gates are consolidated in [completion report](COMPLETION_REPORT.md) and [operations](OPERATIONS.md).
