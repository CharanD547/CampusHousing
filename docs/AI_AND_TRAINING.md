# Roomwise assistant and Gemma workflow

## Assistant modes

`/#assistant` and `/api/v1/assistant/messages` support two answer paths:

- **Local helper (`local_rules`)**: deterministic, needs no model and no credentials. It explains installment billing, summarizes the selected comparison, reports missing costs and route coverage, and suggests before-signing questions. Unsupported questions get an explicit insufficient-evidence response. It answers with `provider: local_rules` and `model_id: null`, and does not consume the model quota.
- **Local Gemma (`openai_compatible`)**: posts the scoped assistant prompt to a loopback model server at `/v1/chat/completions`, then validates the model alias, the JSON structure and citation IDs. If the model output fails validation, the app falls back to the local helper.

Model calls are limited to one at a time, with an explicitly configured persistent UTC daily attempt cap (30 by default, 200 in the current local setup). Failed attempts count toward the cap, requests are not retried automatically, and request IDs are replay-protected. Chat is session-only in the browser and is not exported to training data. These controls do not independently establish that every generated sentence is factually accurate.

The limit is explicitly configured in `ROOMWISE_AI_DAILY_REQUESTS`; configuring a model does not automatically raise it. The current local configuration uses 200. The assistant now sends compact comparison facts, validates cited candidate IDs and monetary amounts, and requires per-person, whole-unit and installment labels where relevant. These checks catch some unsupported answers; they do not prove every claim is grounded. A failed validation returns the deterministic helper with `provider: local_rules`, no model ID and an explicit `fallback` notice. Browser requests allow 35 seconds; inference transport remains bounded to 25 seconds with a 30-second response wall-clock limit.

## Local Gemma setup

Weights used: `google/gemma-4-E4B-it`, revision `ee0ef6023621cff504d758262d4e04895a5af4a2`, stored in `var/models/gemma-4-E4B-it/`. Training and serving ran on a local NVIDIA GPU with about 24 GB VRAM, using a separate environment at `var/training-venv/` so the production API environment stays free of torch.

Start the model server (loopback only, port 8002):

```powershell
var\training-venv\Scripts\python.exe tools\training\serve_gemma.py --model var\models\gemma-4-E4B-it --adapter var\models\roomwise-gemma-4-e4b-lora-cont\adapter --alias roomwise-gemma-4-e4b-v2 --port 8002
```

Check it with `GET http://127.0.0.1:8002/health`. The health check only confirms that the weights and adapter loaded. It does not establish answer quality.

Point a backend at it. Use environment variables so `.env` stays unchanged:

```powershell
$env:ROOMWISE_AI_PROVIDER='openai_compatible'
$env:ROOMWISE_AI_MODEL='roomwise-gemma-4-e4b-v2'
$env:ROOMWISE_AI_BASE_URL='http://127.0.0.1:8002/v1'
$env:ROOMWISE_EXTERNAL_ENABLED='true'
```

`ROOMWISE_EXTERNAL_ENABLED` also gates calls to the local model process despite its name. Keep it `false` unless that server is running. The loopback model server needs no API key. Use a distinct alias for each adapter version.

## Dataset

```powershell
.\.venv\Scripts\python.exe tools/training/prepare_dataset.py
.\.venv\Scripts\python.exe tools/training/train_gemma.py --report var/training/preflight.json
```

The dataset in `var/training/roomwise-synthetic-v1/` has 240 authored examples: 192 train, 24 validation and 24 test. Context groups do not overlap between splits, but templates are shared across them. The data is therefore a pipeline and evaluation starter, not a validated generalization benchmark. No collected resident reviews were used (`raw_review_records_used: 0`). Their training-use permission has not been established.

## Training runs

Both runs used LoRA (rank 16, alpha 32, dropout 0.05) on the text-decoder `q/k/v/o` projections, with prompt tokens masked from loss. Base weights are unchanged.

| Run | Output | Validation loss before → after | Notes |
|---|---|---|---|
| v1 | `var/models/roomwise-gemma-4-e4b-lora/` | 4.72 → 0.019 | 2 epochs, LR 2e-4 |
| v2 (continued from v1) | `var/models/roomwise-gemma-4-e4b-lora-cont/` | 0.019 → 0.00003 | 2 more epochs, LR 1e-4 |

The v2 loss is near zero on templated data, which suggests memorization of the authored templates rather than better general behavior. Use the generation evaluation below as the real quality signal.

Training reports: `training-report.json` in each output folder. Historical reports retain the original dataset manifest's Gemma 3 label; do not rewrite those historical reports as new experiments. New dataset preparation now names Gemma 4 E4B, and future local training reports distinguish a declared revision from a Hub-resolved revision. Local paths alone do not establish the weight revision. Optional training requirements now list the observed top-level versions; they are not a complete transitive lock.

## Held-out generation evaluation

Each model answered the same 24 held-out test prompts through the serving endpoint. Results are in `var/training/*-gemma4-e4b-evaluation.json`.

| Model | Schema valid | Citations valid | Answer kind correct |
|---|---|---|---|
| Base Gemma 4 E4B | 100% | 100% | 25% |
| v1 adapter | 100% | 100% | 58% |
| v2 adapter | 100% | 100% | 79% |

"Answer kind correct" is an automated check on the answer category, not a review of factual support. Schema and citation validity show only that the output is well-formed and points at real IDs. They do not show that a claim is grounded. Manual review of groundedness, billing correctness, uncertainty and prompt-injection cases is still required before any quality claim beyond these numbers.

## End-to-end check

A backend with the v2 adapter (port 8003) answered a live assistant question about a saved comparison. The request returned `status: complete` with `provider: openai_compatible` and `model_id: roomwise-gemma-4-e4b-v2` in about 7.6 seconds. The model server handled one `/v1/chat/completions` request in that run.

## Limits and remaining work

The current main app on port 8001 is configured for the existing v2 local server on port 8002. Review testing found a correct Grove asking-price answer, successful installment/availability/safety refusals, awkward templated wording, and an incorrect description of the Mill installment as a term total. The billing guard now rejects that error and falls back explicitly. See `HOUSING_UPDATE_REVIEW.md`. No retraining was performed during this review.

- The test set shares templates with training, so the 79% figure overstates performance on new real questions.
- No independent, human-written evaluation set exists yet.
- Real review data is not approved for training.
- The `/api/v1/ai/explain` endpoint still uses `UnconfiguredGemmaRuntime`. Setting the chat transport does not configure it.
- Hosted inference needs a compute choice, private artifact storage, access control and a budget.

Do not describe the model as a fine-tuned product feature beyond this measured local evaluation. The base model's license applies separately from the application's MIT license.
