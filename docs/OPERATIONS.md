> Current submission status: see [the October 25 rubric review](RUBRIC_IMPROVEMENTS_2026-10-25.md). Some routing details below describe backend compatibility paths; the class-schedule UI is removed.

# Roomwise operations

Local prototype, October 24, 2026. The requested LAN development run now binds to `0.0.0.0:8001` with an operator token; see [LAN instructions](LAN_DEVELOPMENT.md). The current `.env` enables Maps, Places and the separately validated Routes credential. Model calls remain disabled. Localhost operator access is explicitly enabled; LAN clients still require the operator token. Never commit real credentials or paste private provider credentials into the application's operator-token form.

## Maps and routing

`GET /api/v1/maps/config` exposes only the designated Maps JavaScript browser key. Places and Routes credentials remain server-side. Browser Maps was rendered and nearby cafes returned live results in Chrome. Grocery search exercised a valid empty result. Empty results remain distinct from proof that a category is absent.

Nearby search is explicit, uses 0.62/1.55/3.11-mile radius labels (meter-based provider requests), and supports groceries, restaurants, gas stations, cafes, pharmacies and libraries. It requests names, addresses, Maps links and attribution, without photos or reviews. Results are not cached or included in saved decisions/model prompts. Official Maps attribution assets are used under Google's attribution guidelines; they are not MIT-licensed Roomwise artwork. Public `/privacy` and `/terms` disclose data flows and link Google's terms/privacy.

Routing supports `single_date` or `representative_week`. Weekly scope expands Monday–Sunday around the selected date and counts every class meeting separately. Transit requests subtract the arrival buffer, apply America/New_York/DST, and supply UTC arrival time. Static walk/bike/drive requests do not claim future closures, parking time, accessibility or indoor walking. Unsupported transit dates remain unsupported. No alternate date is silently selected.

Routes results are transient. Saved comparisons/briefs exclude provider durations and derived commute verdicts; saved route coverage becomes unknown and asks for fresh estimates. This also keeps live provider content outside model context. The adapter deduplicates identical property/building/mode/arrival requests within a comparison, allows at most 12 attempts and checks a 12-second scheduling budget. Transport timeouts bound individual network operations; this is not a strict network wall-clock SLA. The shared persisted Places/Routes daily attempt limit defaults to 40, with failures charged against it. SDK browser usage is outside that cap. Configure provider-side restrictions and quotas in the owner account before sharing.

Official references: [Routes request fields](https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRoutes), [Routes policies](https://developers.google.com/maps/documentation/routes/policies), [Places policies and attribution](https://developers.google.com/maps/documentation/places/web-service/policies), [accessible markers](https://developers.google.com/maps/documentation/javascript/advanced-markers/accessible-markers).

## Access and accounts

Default mode is a loopback-only local operator. A configured `ROOMWISE_API_TOKEN` protects APIs with a bearer header; this token alone does not isolate students. Cross-site browser API requests and untrusted hostnames in default local mode are rejected. Request logs contain route templates, method, status, request ID and elapsed time, not schedules/questions/passwords/provider responses.

Optional `ROOMWISE_ACCOUNTS_REQUIRED=true` adds local username/password accounts. Passwords are salted PBKDF2 hashes; session tokens are random, hashed in storage, expire after 24 hours, use HttpOnly/SameSite Strict cookies and use Secure cookies under HTTPS. Registration/login attempts are limited. Each workspace/comparison/brief has an owner; unauthorized reads, writes, exports, trash and restore return 404. Legacy records stay owned by the local operator and are not assigned to the first account. Per-account browser cache keys keep separate accounts' drafts apart within the UI; anyone with filesystem/browser-profile access can still inspect those local files.

Accounts are disabled in the existing instance to preserve its private operator workflow. Enabling accounts requires a restart; existing operator data stays separate. There is no email verification, password recovery, account deletion or managed cloud identity. Use TLS and an appropriate identity/recovery system before a shared public deployment. The interface must not be advertised as production account security.

## Recovery and backups

The Data page lists up to 200 newest records per collection for the current operator/account. JSON export contains private notes/schedules. Moving a workspace or brief to trash blocks API reads and edits; restore returns its original revision/body. Trash is retained indefinitely until an operator performs a documented purge. It is not full deletion of related immutable snapshots, browser drafts, backups or downloaded exports. No permanent purge was run during this work.

Use `tools/backend/backup.py backup SOURCE NEW-DESTINATION` for SQLite snapshots and a checksum manifest. Use `restore BACKUP NEW-DIRECTORY` for prevalidated restoration without overwriting current storage. Integrity, checksum and path validation reject corrupt/tampered inputs. Backups contain account hashes/session records if present: protect them like the original private data. Backing up an active server is consistent per database, not a cross-database transaction. Stop writes first if a coordinated application snapshot is required.

The completed drill copied and restored seven databases under ignored `var/backups/completion-20261024/` and `var/recovery-drill-20261024/`. `.env`, browser storage and model weights are excluded. The drill backup predates the final Mill source recheck. A separate final backup, including that source update and the saved weekly workspace, is at `var/backups/final-20261024-1644/`; neither claims to capture later writes.

## Deployment verification

`requirements-lock.txt` installed successfully in a new `.venv-release-check` environment. `tools/backend/verify_release.py` started an isolated instance with fresh storage, exercised the production HTTP flow, then stopped it. This does not establish Linux/container compatibility.

The Dockerfile runs as UID 10001 with `/app/var` writable, locked dependencies and a health check. `compose.yaml` binds only `127.0.0.1:8001`, requires an operator token, provides a persistent named volume, and leaves AI disabled. It starts fresh storage, not the host's `var/` automatically. Docker/gcloud are not installed here, so the recipe is unbuilt and undeployed. Do not deploy local SQLite to ephemeral instance storage or imply that Firestore migration exists.

Read-only diagnostics: `tools/backend/audit_readiness.py --report var/readiness-audit.json`. This checks catalog coverage/configuration/database integrity; it does not reverify live rent availability. Model preflight likewise proves dataset/dependency checks only, not trained-model quality.
