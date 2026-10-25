# Contributing to Roomwise

Thanks for helping make housing decisions clearer. Useful contributions include better source evidence, clearer pricing and billing explanations, accessibility fixes, independent model evaluation and reproducible deployment.

## Set up

Follow the [quick start in the README](README.md#quick-start). The application runs locally with providers disabled, so you do not need API keys or a GPU for normal development.

## Before you open a pull request

Run the checks that CI runs:

```bash
python -m pytest -q
node --test tests/frontend_adapter.test.cjs tests/property_map.test.cjs
python tools/build_frontend.py
python tools/backend/export_contracts.py
```

If you change the API, regenerate the contracts and include the updated files. If you change housing data, say where the new evidence came from and when it was checked.

## Keep these out of issues and pull requests

- `.env` files, API keys, bearer tokens and private workspace data
- Raw resident reviews or any text whose reuse permission is not established
- Local databases from `var/`, and base model weights

## Scope

Keep changes focused. Asking prices are dated snapshots, so do not present them as final quotes. Deterministic cost calculations stay in application code; the optional model may explain results but must not change amounts.

For security problems, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
