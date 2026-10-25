# Roomwise submission readiness

Reviewed against the supplied **GDG Build with AI x Hacktoberfest 2026 (1)** deck, especially pages 12–15. These are readiness findings, not predicted judging scores.

## Event requirements

- The deck specifies Sunday, October 25, **11:00 AM–12:30 PM** for submissions, with a hard **12:30 PM** deadline.
- Page 12 requires **two separate submissions**: MLH and the **Virginia Tech chapter entry on codingjam.dev**. One does not substitute for the other.
- Include a public GitHub repository, an open-source license, project description, technologies and a **two-minute demo video**.
- The later submission slide says **select only one MLH track**, despite earlier slides saying multiple tracks are possible. Follow the specific submission instruction or an explicit organizer clarification. No submission has been made by this readiness work.
- The deck confirms Best Use of Gemma 4, Best Open-Source AI Project, Best Use of Google Cloud and Best UI/UX; GDG separately judges Best Overall AI for Housing. Do not claim Google Cloud backend/inference deployment from Google Maps usage alone.

## Scoring evidence and remaining gaps

| Criterion | Points | Current evidence | Remaining limitation |
|---|---:|---|---|
| Problem definition | 10 | Virginia Tech housing search; mixed room/unit/installment pricing and incomplete fee information | Keep the demo focused on avoiding an incorrect affordability comparison |
| Impact multiplier | 10 | 44 priced properties, 304 plans, a 47-reference directory and reusable written-quote requests | No measured time savings, financial savings or adoption study; do not claim them |
| Stakeholder empathy | 5 | Realistic student/roommate scenarios; user's observed pricing and UI problems drove fixes | No documented external participant interview/usability study |
| AI integration and necessity | 15 | Local Gemma 4 E4B LoRA interprets sourced housing evidence and explains unresolved terms; direct plan-to-assistant workflow | Deterministic helper can substitute; Gemma output remains fallible. Show an actual identified model answer and explain its useful language task |
| Architectural soundness | 10 | Same-origin FastAPI/SQLite; deterministic arithmetic; source versions; frozen briefs; generated OpenAPI; tests | Single-operator local deployment; backend's inclusive catalog verdict is not a verified preference match |
| Safety and grounding | 10 | Allowed source/candidate IDs, amount and billing-label checks, honest fallback, no automatic actions | Validation is not entailment checking or complete hallucination detection |
| Privacy and data ethics | 8 | Chat is session-only; no raw reviews in prompts/training; public synthetic training bundle; copy-only quote requests | Review reuse permission is unresolved; hosted provider use transmits scoped context |
| Inclusive design | 7 | Native controls, labels/live status, keyboard and phone testing, text alternatives to maps | No claim of full WCAG certification or assistive-technology audit |
| Deployment viability | 10 | CPU-only local setup and Docker recipe; no model credentials required for deterministic browsing | No verified public cloud deployment; Docker cannot be executed on this host because Docker CLI is absent |
| Inference cost efficiency | 8 | One model request at a time; capped attempts, bounded history/context; deterministic arithmetic; explicit fallback; shared Maps cap | Current CUDA recipe uses about 24 GB VRAM; no quantized CPU/mobile runtime or measured cloud cost |
| Documentation and maintenance | 7 | Setup, contracts, model card, frozen synthetic dataset/reports, source recheck and per-property follow-up list | A clean-machine GPU inference reproduction remains unverified; public adapters include hash manifests and run instructions |

## Recommended demo and track positioning

Use [the two-minute demo script](DEMO_SCRIPT.md). Present Roomwise as a **source-backed housing research assistant**, not a rent guarantee, legal adviser or neighborhood-safety scorer. For Gemma, show the exact local model/adapter identity and a useful supported answer. The open-source entry has a reproducible code/data story; the Gemma entry needs a dependable live model demonstration. Choose the single MLH category in the actual event form.

The training dataset is now in `data/training/roomwise-synthetic-v1/`; the same historical data hashes are retained. See [the model card](MODEL_CARD.md) for the stale Gemma 3 manifest-label explanation, experiment limitations and licensing. Both historical dataset versions and the actual v1/v2/v3 LoRA adapters are bundled; v2 remains selected. Base weights are excluded. Current rental prices are not memorized into training examples. See `models/README.md` for licensing, hashes and loading instructions.

## Before submitting

1. Capture a real two-minute video of the working flow; show model identity, source dates and missing costs.
2. Have one other student attempt a housing task. Record consent, task completion, misunderstandings and their exact feedback; do not invent a testimonial or outcome.
3. Commit/push the tested source, public synthetic dataset and docs after the secret scan. Keep keys, workspaces, reviews, environments, base weights and pickle checkpoints excluded; publish only the explicitly packaged learned adapters.
4. Confirm the event form's category/deadline, submit to both required platforms, and verify the receipt/gallery entry. These external submission actions have not been performed.
5. Request the operator follow-ups in [the complete fees/lease list](FEES_AND_LEASE_QUOTES.md). Current asking figures are sufficient for a research demo, not a final lease decision.
