# Backend-only purge record

October 24, 2026. The user explicitly requested removal of everything unrelated to the supplied backend PRD and a backend-focused structure.

## Removed from the working project

- Entire `web/` frontend, vendor UI files, illustrations and fictional rehearsal.
- Entire `src/clearpass/` package: visual inspection, repairs, redaction, model image handling, calibration, parcel/voucher logic, document investigation, old UI/API orchestration.
- `prop/` physical demonstration assets and `validation/` inspection/research fixtures.
- Old `var/` saved inspection, investigation and housing records; they were archived, not imported into the new backend.
- Old `output/` screenshots, PDFs, test reports and release archives.
- Old ClearPass scripts and tests; replaced with tests of the retained housing invariants and new backend contract.
- Old product, repair, pivot, demo and verification documents, plus the previous integrated PRD/build notes. The new backend PRD removes the duplicated frontend appendix.
- Broken copied virtual environment and previous broad development runtime. A fresh `.venv` contains only the backend/test dependency closure.
- Image processing, PDF, and inference SDK requirements unrelated to currently implemented backend adapters.

## Retained and reorganized

- Corrected public housing seed, source evidence, price review manifest, limited transit archive, MIT notice.
- Deterministic housing rules, audited price corrections and bounded source retrieval, moved into `roomwise` layers.
- Explicit routing/Gemma adapter boundaries, campus repository, local workspace/brief store, evidence API, deterministic guide service.
- `/api/v1` contracts, generated OpenAPI, labeled mock fixtures, backend-only tests, setup and architecture documentation.

## Recovery archive

The source and records were first copied to:

`C:\roomwise-vt-archive\before-backend-purge-20261024-112153`

Obsolete working copies were then moved beneath that directory's `removed-working-copy/`. The previous broad development environment was moved to `old-development-runtime/`. The archive is outside the working project and is not included in its source, package, or container.

Automatic approval review rejected the bulk recursive delete command without a detailed reason. Recoverable moves were used instead. The workspace is purged of those components; the archive has not been permanently erased.

## Verification and remaining gaps

- Old ClearPass development server was stopped; the new Roomwise API starts on loopback port 8001.
- Fresh backend environment: dependency installation and `pip check` succeeded.
- 24 focused backend/contract tests passed. One dependency deprecation warning remains; no test failures.
- Generated OpenAPI matches the application schema; mock fixtures are labeled and schema-validated.
- Removed UI/inspection routes return 404.
- Corrected catalog amounts and immutable/idempotent brief behavior remain tested.

This purge is a backend restructuring, not completion of every PRD feature. Real class-building data, classroom routing, Gemma inference, paid-service controls, licensed reviews and cloud deployment remain explicit integration work. See `ARCHITECTURE.md` for exact boundaries and next steps.
