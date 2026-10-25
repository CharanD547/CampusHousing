---
base_model: google/gemma-4-E4B-it
library_name: peft
license: apache-2.0
tags:
- lora
- roomwise
---
# Roomwise Gemma 4 E4B v1 LoRA adapter

Historical experiment; not the selected runtime.

This folder contains the actual learned tensor deltas, not the base model.
Load using PEFT with the separately obtained base model and its tokenizer.
See [the model card](../../docs/MODEL_CARD.md), [package instructions](../README.md),
[training report](../../data/training/reports/v1-training.json) and manifest hashes.
Synthetic shared-template evaluation does not establish factual accuracy.
Apache-2.0 applies to this adapter; see [LICENSE](../LICENSE) and [NOTICE](../NOTICE).
