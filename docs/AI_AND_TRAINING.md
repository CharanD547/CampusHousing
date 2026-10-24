# Roomwise assistant and Gemma workflow

## What works without API credentials

Open `/#assistant`. With model operations disabled, `/api/v1/assistant/messages` uses a deterministic local research helper. It explains installment billing, summarizes the selected comparison, reports missing costs and route coverage, and suggests before-signing questions. Unsupported questions receive an explicit insufficient-evidence response. It does not browse websites, analyze the collected reviews, execute actions, change prices or claim to be Gemma.

Answers identify `provider: local_rules` and `model_id: null`. Property questions use the saved comparison and its catalog snapshot; cited sources are links to the reviewed housing evidence. Route coverage is a fact about the saved comparison, not a new route calculation. General guidance is labeled separately. Chat is session-only in the browser and is not exported to training data.

Model transports are implemented for `google` and `openai_compatible`; no production model call has been verified. The assistant applies scoped context, structured-output and citation checks, one request at a time, a persistent UTC daily attempt limit, and request-id replay protection. Failed attempts count toward the cap; requests are not automatically retried. The local research helper makes no model calls and does not consume the model quota. These controls do not independently establish the factual accuracy of every generated sentence.

The earlier comparison explanation endpoint remains an optional Gemma boundary; local helper text is not presented as a successful model explanation. Live Maps and on-demand nearby Places are integrated. Live walking/transit estimates have now been verified with a separate Routes credential; the full coverage matrix remains incomplete. Google Search grounding is unimplemented, and provider Places content is excluded from saved model context. See the [expanded remaining-work checklist](COMPLETION_REPORT.md#still-blocked-or-intentionally-incomplete).

## Prepared training dataset

```powershell
.\.venv\Scripts\python.exe tools/training/prepare_dataset.py
.\.venv\Scripts\python.exe tools/training/train_gemma.py --report var/training/preflight.json
.\.venv\Scripts\python.exe tools/training/evaluate_gemma.py
```

These commands require no model/API credentials and do not download weights. They author and check **240 synthetic examples**: 192 training, 24 validation, 24 test. Examples teach structured answers, evidence IDs, uncertainty, billing basis, partial routing and handling instructions embedded in untrusted content. They use fictional counterfactual contexts and authored targets, not original review passages or student conversations.

Output: `var/training/roomwise-synthetic-v1/`. The manifest records content hashes, source scope, split method and the proposed base model/revision. Context groups do not overlap between splits. Templates do overlap, so these are pipeline checks, not a validated generalization benchmark or proof of a useful fine-tuned model. The default evaluation checks target data only; it explicitly reports `inference_performed: false`.

The 720 collected reviews, including 67 VT records, remain research-only. They have not become labeled, privacy-reviewed, authorized training data. Before incorporating resident text, establish training-use scope and create reviewed labels with source IDs, dates, property scope, aspect annotations and uncertainty. Split real examples by property/source/time, remove near-duplicates, and retain a genuinely held-out evaluation set. Do not train a model to memorize supposedly current rent or availability; retrieve those facts at inference time.

## Actual LoRA training: not yet run

The starter recipe targets Google's [Gemma 3 1B instruction model](https://huggingface.co/google/gemma-3-1b-it), pinned to the observed base revision `dcc83ea841ab6100d6b47a070329e1ba4cf78752`. It trains query/key/value/output projection adapters, masks prompt tokens from loss, preserves the base weights, records package versions and pre/post validation loss, and saves a separate adapter. See Google's [Gemma tuning guidance](https://ai.google.dev/gemma/docs/tune).

Local inspection found an NVIDIA RTX 5090 Laptop GPU with approximately 24 GB VRAM. This is a promising candidate for the 1B LoRA recipe; CUDA/PyTorch compatibility and actual peak memory have not been tested. No Torch/Transformers/PEFT training stack is installed in the API environment. The normal local Hugging Face cache contains no Gemma model. Official model access is gated, and no Hugging Face token was present in the inspected process environment. No weights were downloaded and no trained model exists.

When authorized model files/access are available, install the optional requirements into a **separate** environment and select a CUDA-enabled PyTorch build compatible with this GPU. Resolve and save a dependency lock for that runtime; `tools/training/requirements.txt` is a starter range file, not a tested lock. The API additionally needs FastAPI/httpx/uvicorn if that training environment will serve or evaluate the model. Do not add the training stack to the production API image.

```powershell
# Run only from a prepared training environment with authorized model access.
python tools/training/train_gemma.py --train
```

Output defaults to `var/models/roomwise-gemma-1b-lora/`. Existing adapter output is not overwritten. Training reports distinguish validation loss from task quality; lower loss alone is not evidence of improved factuality or usefulness. The script validates chat-template prefix masking before training rather than guessing the prompt boundary.

## Serve already-downloaded weights locally

The local server requires no cloud API. It loads existing local base weights and an optional adapter, with model downloads disabled. It binds to loopback port 8002 and accepts one bounded generation at a time. This serving recipe has been syntax-checked but has not run with actual weights.

```powershell
python tools/training/serve_gemma.py --model C:/path/to/local/gemma-base --adapter var/models/roomwise-gemma-1b-lora/adapter --alias roomwise-gemma-1b-v1
```

In the separate Roomwise backend process, set:

```powershell
$env:ROOMWISE_AI_PROVIDER='openai_compatible'
$env:ROOMWISE_AI_MODEL='roomwise-gemma-1b-v1'
$env:ROOMWISE_AI_BASE_URL='http://127.0.0.1:8002/v1'
$env:ROOMWISE_EXTERNAL_ENABLED='true'
```

Despite its name, this switch also gates calls to a separate local model process. Keep it false until that runtime is intentionally running. No provider key is required for the loopback model server. Use a distinct model alias for each adapter/version. Loading an adapter is not proof that its responses pass evaluation.

## Evaluate before claiming improvement

Run the base model first, then the adapter under a different alias, against the same held-out file:

```powershell
python tools/training/evaluate_gemma.py --generate --model roomwise-gemma-base --output var/training/base-evaluation.json
python tools/training/evaluate_gemma.py --generate --model roomwise-gemma-1b-v1 --output var/training/adapter-evaluation.json
```

Each command expects the corresponding alias to be running at `http://127.0.0.1:8002/v1`. Generation evaluation measures schema validity, citation/candidate validity and expected answer kind. Manually review groundedness, financial/billing correctness, uncertainty, unsupported questions, prompt injection and latency as well. Citation validity does not establish that an answer's claim is actually supported.

Do not publish a “custom trained Gemma” claim before a real run, saved adapter, reproducible training report and held-out generation evaluation exist. Keep the base model's terms separate from the application's MIT license. The current delivered work is the working local helper and prepared, unexecuted model workflow.
