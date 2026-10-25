# Roomwise: pitch and demo playbook

**One sentence:** Roomwise helps Virginia Tech students understand housing prices, compare the known costs, and identify what they still need in writing before choosing a lease.

**Recommended positioning:** source-backed student housing research, with a locally fine-tuned Gemma 4 assistant. For a Gemma entry, demonstrate a real answer labeled `roomwise-gemma-4-e4b-v2`. Choose the single MLH track requested by the final submission slide; do not claim cloud hosting from Maps usage.

## Two-minute spoken pitch

The quoted text below is the script. Actions are separate; rehearse the combined timing and allow the assistant time to respond. Target about 110–120 spoken words per minute. Skip optional map interaction if inference takes longer.

| Time | Say | Show / do |
|---|---|---|
| 0:00–0:18 | “A housing listing says nine hundred dollars. Is that per person, per apartment, or one installment? What about utilities and deposits? For a student comparing leases, those differences can change the decision.” | Explore. Use the number only as this hypothetical example, not a claim about a visible listing. |
| 0:18–0:35 | “We built Roomwise for Virginia Tech students. It brings forty-four priced properties and three hundred four plans into one research workflow, with one card per property, clear billing labels, and links to the evidence.” | Open a rehearsed property and its plan selector. Point at a source and billing basis. |
| 0:35–0:52 | “I can shortlist plans and compare the known costs. The backend handles the arithmetic. Missing fees stay unknown, and a roommate split stays a planning scenario rather than a promise about the lease.” | Compare two prepared plans. Point at the known subtotal and an unresolved charge or term. |
| 0:52–1:20 | “Our assistant uses Gemma four, fine-tuned locally with LoRA on authored synthetic housing examples. It helps explain the selected evidence and what to ask next. Current rents come from the evidence, not model memory. Validation checks source identifiers, amounts, and billing labels; rejected output falls back visibly.” | Property → “Ask the assistant about this plan.” Submit the rehearsed question below. While it runs, explain the model. Point to the actual provider/model label, source and limitation. |
| 1:20–1:36 | “Roomwise then turns uncertainty into action: a written-quote request for the exact plan, fees, dates, payment count, and availability. Copying this request sends nothing to a landlord.” | “Before you commit” → copy the quote request. Show its text or copy confirmation. |
| 1:36–1:47 | “Students can also investigate nearby essentials, with distances in miles, then save a brief that preserves the evidence behind their comparison.” | Show the nearby panel without triggering extra paid searches; show a prepared saved brief. |
| 1:47–2:00 | “The code, both synthetic dataset versions, trained adapters, and evaluation reports are public. This is a working local prototype. Our goal is simple: help students know what they are comparing, and what they still need to verify.” | Public repository: `models/README.md` and `docs/MODEL_CARD.md`. End on Roomwise. |

**Assistant question to rehearse:** “Explain this plan's asking price and billing basis. Which fees and lease facts should I confirm in writing?” Use the exact selected plan context. Do not promise a particular answer in advance.

## Prepare the demo

1. Use a demo-only browser profile/workspace or back up the current workspace first. Do not overwrite personal notes or remove a real shortlist to prepare the recording.
2. Start the backend and the already configured v2 model server. Confirm Explore loads and the assistant names the expected model. A health response alone does not prove generation works.
3. Prepare two plans with different, clearly visible billing bases. Foxridge and the Mill are useful candidates, but verify the exact selected plan and displayed labels before recording. Avoid reading a price from memory.
4. Rehearse Compare, the property evidence link, “Ask the assistant about this plan,” the quote request and one saved brief. Make the saved brief using the prepared demo data before recording.
5. Run the assistant question once before recording. Allow one request to finish; do not stack retries. If it falls back, use the fallback line below and keep its actual label visible.
6. Prepare the nearby panel in advance. Respect the authorized shared Google web-service cap of 60 daily attempts; browser SDK quotas are separate. An existing panel is enough to explain miles and nearby categories.
7. Keep three tabs ready: Roomwise, the public GitHub repository/model card, and the required submission form. Hide terminals, `.env`, tokens, private notes and unrelated notifications.
8. Record one 120-second screen-and-voice take at a readable desktop zoom. Keep the cursor near the element being discussed. Use short pauses instead of opening many menus. Review the exported video for readable labels, intelligible audio and exposed private data before uploading.

## Honest recovery lines

- **Model rejects an answer:** “This response did not pass validation, so Roomwise is showing its labeled local helper. The comparison and sources still work. That label matters: we do not present the helper as a Gemma answer.”
- **Model is slow or busy:** “Local generation is limited to one request at a time. While it finishes, here are the source and the missing terms the assistant is working with.” Move to the quote request; do not repeatedly click Ask.
- **Nearby service unavailable:** “Nearby search depends on the configured map provider. The housing evidence and comparison remain usable.” Use the existing text panel or continue the demo.
- **A price cannot be confirmed:** “This is a dated asking figure, not a verified available lease quote. These are the specific facts we still need from the operator.”

A clearly dated recording of an earlier real model response can be a backup if disclosed as a recording. Do not stage a fake successful answer or relabel a deterministic response.

## Judge questions: concise answers

**Why does this need AI?**

“Arithmetic does not need AI, so we keep it in code. The useful language task is explaining evidence and ambiguous renting terms in a student's question, then identifying what is still missing. Gemma supports that task inside a constrained evidence context.”

**What exactly did you train?**

“We adapted `google/gemma-4-E4B-it` with rank-sixteen LoRA on text-decoder query, key, value and output projections. The selected v2 adapter continued v1 training. We published the actual tensor deltas, both historical synthetic dataset versions, training code, manifests and reports. Base weights are obtained separately.”

**How much data? Did you train on residents' reviews?**

“The selected model used 240 authored synthetic examples: 192 training, 24 validation and 24 test. A second 240-row version was used for the v3 experiment; the versions overlap and share templates. No resident reviews, user chats, private workspaces or current rent records went into these datasets.”

**How did fine-tuning perform?**

“On the same 24 shared-template generation cases, answer-category correctness rose from 25 percent for the base model to about 79 percent for v2. This is not factual accuracy or independent real-world validation. v3 regressed and was not selected. We published the unfavorable results too.”

**What prevents hallucinations?**

“We bound the evidence context and check response structure, allowed sources and candidates, money amounts and billing labels. Some unsupported outputs are rejected with an explicit fallback. These guards reduce specific failures; they do not prove every sentence follows from its source.”

**Is the rent data live and complete?**

“It is timestamped source research, not a live leasing inventory. We rechecked source pages and preserve billing basis and uncertainty. We still need individualized written quotes and complete mandatory fees. The app exposes those gaps and generates the right follow-up request.”

**How is this different from a listing site?**

“The focus is understanding a comparison: one property with multiple plans, explicit room versus whole-unit versus installment labels, known subtotals, unresolved charges, dated evidence, and a saved research brief. We help move from browsing to a concrete verification step.”

**What is actually deployed, and what does it cost?**

“The tested prototype runs locally with FastAPI, SQLite and a browser UI. The model serves locally on CUDA; the measured recipe needs about 24 GB VRAM. Requests are serialized and capped, and provider requests have budgets. We have not verified public cloud deployment or measured a hosted per-user cost.”

**What about privacy and inclusion?**

“Chat stays in the browser tab and is excluded from training. The configured provider receives the scoped question, recent history and selected public evidence. Private workspace notes and raw resident reviews are excluded from prompts. We refuse demographic exclusion rankings and avoid neighborhood-safety scores. We tested keyboard and phone use, without claiming accessibility certification.”

**What would you improve next?**

“First, obtain written plan-specific quotes and complete fee schedules. Then run consenting-student usability tasks and an independent evidence-grounding evaluation. After that, verify a smaller inference runtime and a public deployment with measured cost and proper account isolation.”

## A fifteen-second version

“Roomwise helps Virginia Tech students understand housing prices before choosing a lease. It keeps billing labels, known costs and missing fees visible, then uses a locally fine-tuned Gemma assistant to explain sourced evidence and prepare the questions students should ask in writing.”

## Submission handoff

The supplied event deck calls for a public repository, open-source license, project details and a two-minute video, with separate MLH and Virginia Tech chapter submissions. Its final submission slide says to choose one MLH track. Check [SUBMISSION_READINESS.md](SUBMISSION_READINESS.md) for the stated deadline and checklist. Preparing this pitch and pushing the code does not submit either entry.

Do not claim guaranteed rents or availability, measured savings/adoption, independent 79-percent factual accuracy, complete review permission, a Google Cloud deployment, or zero bugs. Show the actual model/provider label and the actual unresolved evidence.
