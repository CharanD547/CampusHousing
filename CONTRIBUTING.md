# Contributing to Roomwise

Start with the [README](README.md) and [documentation index](docs/README.md). The current project is a local housing research prototype for Virginia Tech. Useful contributions include pricing clarity, source corrections, accessibility, independent model evaluation and reproducible deployment.

## Development loop

1. Create a branch from current `main` and follow the README setup.
2. Keep changes focused. Preserve existing saved workspaces and use isolated test storage for state-changing checks.
3. Edit frontend source under `CampusHousing-main/src/`; run `python tools/build_frontend.py` after shell/CSS changes. Do not hand-edit the generated `index.html`.
4. For API/schema changes, regenerate with `python tools/backend/export_contracts.py` and inspect the diff.
5. Run relevant checks, then the required regression checks before submitting:

```bash
python -m pytest -q
node --test tests/frontend_adapter.test.cjs tests/property_map.test.cjs
```

CI also exercises fresh-storage HTTP flows with providers disabled. It does not establish real model quality, live rent availability or paid-provider behavior. Explain the actual checks and remaining limitations in your pull request; include screenshots for UI changes.

## Housing data

Record the property, exact plan, source URL, date checked, amount/range, billing basis and payment period. Keep asking prices separate from individualized written quotes, research assumptions and unconfirmed guide references. Never turn an unknown charge into zero or a room price into a whole-unit price. Preview imports and catalog syncs before applying them. Existing saved briefs must retain their original evidence.

## Model work

Preserve historical dataset bytes, manifests and unfavorable results. Do not regenerate a dataset in place and describe it as the same historical experiment. New runs need a new version, data provenance, permission to use the data, hashes and honest evaluation. The current synthetic sets share templates and do not establish independent factual accuracy. See the [model card](docs/MODEL_CARD.md).

The three explicitly packaged LoRA adapters under `models/` are intentional Git artifacts. Base weights, duplicate tokenizers, pickle checkpoints, optimizer state and private runtime data belong under ignored `var/`. Do not widen the weight-file ignore exceptions casually.

## Secrets, privacy and licenses

- Never commit `.env`, provider keys, backend tokens, account records, private workspaces, chats or unapproved review text.
- Use synthetic examples in tests. Redact screenshots and error reports.
- Do not activate paid APIs as part of automated tests. Live checks require an owner-approved configuration and budget.
- Retain original licenses/notices. App code and authored synthetic data use MIT; Gemma adapters use Apache-2.0. Provider and source-data terms remain separate.

Report security problems privately as described in [SECURITY.md](SECURITY.md).
