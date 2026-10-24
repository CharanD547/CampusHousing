# Backend integration contract

`v1.openapi.json` is generated from the actual FastAPI routes and Pydantic input/output models. Regenerate using `python tools/backend/export_contracts.py`. Do not edit the generated schema by hand.

`fixtures/*.json` wrap mock payloads with `fixture_mode: true`. They support explicitly labeled frontend mock mode. Synthetic building/offer IDs are intentionally not present in the live catalog. Only the `payload` member represents an API body.

Read `docs/backend/ARCHITECTURE.md` for contract decisions, unavailable provider boundaries, and known release gaps. A successful schema export is not evidence of actual routing or model inference.
