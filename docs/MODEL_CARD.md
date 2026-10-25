# Roomwise local Gemma model card

## Intended use

Gemma explains scoped housing evidence, billing terminology and questions to ask an operator. It does not determine eligibility, make demographic or safety rankings, give legal conclusions, browse on the user's behalf or execute actions. Deterministic application code calculates costs and preserves source records. Property detail pages can open the assistant with that exact plan as context without changing the shortlist.

## Identity and licenses

- Base: [`google/gemma-4-E4B-it`](https://huggingface.co/google/gemma-4-E4B-it), recorded revision `ee0ef6023621cff504d758262d4e04895a5af4a2`.
- Selected local adapter alias: `roomwise-gemma-4-e4b-v2`.
- Application and authored synthetic examples: repository MIT license.
- Base model and published LoRA adapters: [Gemma 4 Apache 2.0 license](https://ai.google.dev/gemma/apache_2), separate from the application license. The actual v1/v2/v3 learned adapters are included under [models/](../models/README.md), with a license, notices and SHA-256 manifests. Base weights, tokenizers and pickle checkpoints are excluded.

## Reproducibility

`data/training/roomwise-synthetic-v1/` contains the exact historical 192/24/24 train/validation/test files and manifest. Split hashes match the copied v1/v2 training reports in `data/training/reports/`. `provenance.json` explains a historical labeling error: the original manifest names Gemma 3, while the actual training reports name Gemma 4 and the revision above. The manifest and data were preserved instead of regenerated to erase this discrepancy.

The 240 examples are authored synthetic renting/evidence cases under MIT. Zero resident reviews, user chats or current property rent records were used. Context groups differ across splits but templates are shared. This is not an independent generalization benchmark.

The second historical dataset version, `data/training/roomwise-synthetic-v2/`, also contains 192/24/24 examples and was used for v3. Its original bytes and manifest match `reports/v3-training.json`. These are two overlapping synthetic versions, not 480 independently authored benchmark cases. v3 used local base weights with a declared but independently unverified revision; its public adapter config leaves the revision null. v1/v2 retain the revision recorded by their training reports.

To run the published selected adapter with separately downloaded base weights:

```powershell
var\training-venv\Scripts\python.exe tools/training/serve_gemma.py --model var/models/gemma-4-E4B-it --adapter models/roomwise-gemma-4-e4b-v2 --alias roomwise-gemma-4-e4b-v2 --port 8002
```

The documented recipe uses rank-16 LoRA, alpha 32, dropout 0.05, text-decoder q/k/v/o projections, masked prompt tokens, BF16 and batch size 1 with gradient accumulation 8. v1 ran two epochs at 2e-4; v2 continued two epochs at 1e-4. The copied training reports preserve observed package versions. See `tools/training/train_gemma.py` and [AI_AND_TRAINING.md](AI_AND_TRAINING.md). The optional training requirements are a top-level version record, not a complete portable lock.

```powershell
.venv\Scripts\python.exe tools/training/train_gemma.py --data data/training/roomwise-synthetic-v1 --report var/training/preflight.json
# With the separate CUDA training environment and downloaded weights:
var\training-venv\Scripts\python.exe tools/training/train_gemma.py --data data/training/roomwise-synthetic-v1 --model var/models/gemma-4-E4B-it --output var/models/reproduction-v1 --train
var\training-venv\Scripts\python.exe tools/training/train_gemma.py --data data/training/roomwise-synthetic-v1 --model var/models/gemma-4-E4B-it --init-adapter var/models/reproduction-v1/adapter --learning-rate 0.0001 --output var/models/reproduction-v2 --train
```

Training preflight verifies data and dependencies; it does not train or establish quality. The existing full-precision CUDA recipe used approximately 24 GB VRAM. Smaller/quantized deployments remain unverified.

## Observed evaluation and limits

| Historical run | Schema valid | Citation IDs valid | Answer category correct |
|---|---:|---:|---:|
| Base | 100% | 100% | 25% |
| v1 | 100% | 100% | 58% |
| v2 (selected) | 100% | 100% | 79% |
| v3 (not selected) | 54% | 46% | 25% |

All four generation reports record the same original 24-case test-file hash. v3 was trained on the second dataset version but was evaluated on that original test file. These figures are **not factual accuracy**, and valid citation IDs do not establish that a sentence follows from a source. Near-zero v2 validation loss suggests template memorization. v3 regressed, so it is not the selected runtime. Historical raw reports are packaged rather than selecting only favorable results.

New application audit prompts are in `data/evaluation/submission-cases.json`; they are separate authored checks, not a human-reviewed benchmark. Run `tools/training/evaluate_application.py` against a local backend with its configured model to retain actual responses and latency. Review money/basis, citation relevance, uncertainty, discrimination and adversarial requests qualitatively. Do not convert transport success or fallback rates into an accuracy claim.

## Safeguards and privacy

The server checks model identity, output schema, allowed candidate/source IDs, monetary amounts across the answer/limitations/follow-up questions, and relevant billing labels. An evidence answer must cite evidence belonging to its selected property. Source snippets and recent history are bounded. These are useful guards, not a proof against hallucinations or adversarial inputs.

The six-case October 25 application audit initially returned six model answers but exposed awkward mixed-language output, unsupported binding-language and a weak discrimination response. Targeted guards now reject unexpected language fragments and unsupported certainty; discriminatory ranking requests receive a clear policy refusal before model inference. The repeat audit returned three model answers, two explicit fallbacks and one pre-inference policy refusal. These small authored checks are not an accuracy estimate. Both response sets are retained under `data/evaluation/`.

Requests run one at a time under a persistent UTC daily attempt cap. Failed validation returns an explicitly identified deterministic helper; it is never called Gemma. Chat is session-only in the browser and is excluded from the training export. Hosted providers would receive the question, bounded recent history and selected public comparison evidence; private workspace notes and raw resident reviews are excluded.
