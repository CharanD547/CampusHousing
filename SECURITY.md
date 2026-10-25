# Security and private-data reporting

Roomwise is a local prototype, not a hardened public housing platform. Only the current `main` branch is maintained; no response-time guarantee or production security certification is claimed.

## Report a vulnerability privately

Use GitHub's private vulnerability reporting on this repository **if it is enabled**. Otherwise contact the repository owner through an existing private channel before sharing details. Do not put exploitable details, credentials or private records in a public issue. No public email address is designated here.

Include the affected commit, reproduction steps using synthetic data, expected impact and any proposed mitigation. Redact credentials and personal information. For an ordinary UI or public source-data correction, use the issue templates instead.

## Operating boundaries

- Keep the default service on loopback. A bearer token is a single-operator access mechanism, not multi-user isolation.
- Optional local accounts do not provide managed identity, password recovery or a complete shared-hosting solution.
- Keep `.env`, runtime databases, exports, backups and browser profiles private. The Data navigation item being hidden is not an access-control boundary.
- Restrict browser Maps keys by origin and provider quotas; keep private Places/Routes/model credentials server-side.
- Treat housing pages, reviews and model output as untrusted data. Validation and fallback reduce specific failure modes but do not prove every generated claim.
- Public shared deployment needs separately verified identity, TLS, persistence, access controls and recovery.
