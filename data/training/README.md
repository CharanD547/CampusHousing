# Public Roomwise training evidence

- `roomwise-synthetic-v1/`: 240 original authored MIT examples, 192 train / 24 validation / 24 test, with original manifest hashes and a separate provenance clarification.
- `roomwise-synthetic-v2/`: the second historical 240-row version used by the v3 experiment, with its exact original bytes and hashes. Dataset versions share templates and may overlap; do not claim 480 unique independent examples.
- `reports/`: historical training and actual-generation evaluation reports, including the weaker v3 run. These reports are observations, not factual-accuracy certificates.
- [Actual v1/v2/v3 LoRA adapters](../../models/README.md) are included separately under `models/`; v2 remains selected. No reviews, chats, workspaces, keys, base weights or pickle checkpoints are included.

See [the model card](../../docs/MODEL_CARD.md). Do not regenerate these files in place and claim the new bytes were used by the historical experiments. To verify/package the existing private runtime copy, run `tools/training/publish_training_bundle.py`; it accepts only matching hashes and authored MIT synthetic rows.
