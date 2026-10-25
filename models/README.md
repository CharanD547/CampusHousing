# Published Roomwise Gemma adapters

These are the actual learned LoRA weights from the local experiments. Each
`adapter_model.safetensors` file is 36,346,288 bytes (about 34.7 MiB), within
GitHub's individual file limit. They are regular Git blobs; Git LFS is not required.

| Folder | Dataset | Status |
|---|---|---|
| `roomwise-gemma-4-e4b-v1/` | `data/training/roomwise-synthetic-v1/` | Initial experiment |
| `roomwise-gemma-4-e4b-v2/` | `data/training/roomwise-synthetic-v1/` | **Selected runtime**, continued from v1 |
| `roomwise-gemma-4-e4b-v3/` | `data/training/roomwise-synthetic-v2/` | Regressed; retained for transparency |

Each manifest records the unchanged tensor SHA-256, original and published config
hashes, training report and dataset. Configs replace the machine-specific base path
with `google/gemma-4-E4B-it`. v1/v2 record base revision
`ee0ef6023621cff504d758262d4e04895a5af4a2`; v3 used a local base directory whose
revision was declared but not independently resolved. Its revision is left null.
These adapters use [Apache-2.0](LICENSE), with changes and attribution in [NOTICE](NOTICE).

## Run the selected adapter

Obtain the base model and its tokenizer separately from the original model publisher,
using the recorded revision above. Keep them in ignored `var/models/gemma-4-E4B-it/`.
The base model is about 16 GB; it is not included in Git. Install the existing optional
CUDA dependencies in a separate environment as described in
[AI_AND_TRAINING.md](../docs/AI_AND_TRAINING.md). The measured recipe needs about
24 GB VRAM; CPU/quantized serving is not verified.

```powershell
var\training-venv\Scripts\python.exe tools/training/serve_gemma.py --model var/models/gemma-4-E4B-it --adapter models/roomwise-gemma-4-e4b-v2 --alias roomwise-gemma-4-e4b-v2 --port 8002
```

The server loads the tokenizer from the base model, so duplicate tokenizer files are
unnecessary. Point Roomwise's configured OpenAI-compatible provider at
`http://127.0.0.1:8002/v1` with the exact alias above. A healthy endpoint establishes
loading, not answer quality. See [the model card](../docs/MODEL_CARD.md) before use.

## Verify without a GPU

```powershell
.venv\Scripts\python.exe -m pytest tests/test_submission_readiness.py -q
```

The package tests validate dataset/report hashes, adapter manifests and safe tensor
structure. They do not rerun training or claim portable inference success.
`tools/training/publish_training_bundle.py` reproduces this public package from the
original ignored experiment outputs; it does not retrain or alter the local runtime.

Base weights, duplicate tokenizers, pickle/checkpoint files, optimizers, caches,
reviews, chats and user workspaces are intentionally excluded.
