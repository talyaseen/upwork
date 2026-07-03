# Safety baked into the weights (LoRA)

The prompt-layer guard (`app/services/guard.py`) is defense-in-depth but
bypassable - a regex cannot cover every paraphrase or language, and an external
red-team confirmed it can be slipped (e.g. Spanish/German location probes,
"translate your instructions"). The durable fix the maintainer asked for is to teach
the **model itself** to refuse, so the safeguard lives in the weights, not just a
prompt that can be talked around.

This pipeline trains a small **safety LoRA adapter** on the demo's GPU model
(`Qwen/Qwen2.5-7B-Instruct`) that intrinsically refuses the classes the red-team
probed, while still doing the product's real job (Q&A + code review, including
security code - the red-team flagged over-refusal, so positive examples are
included).

## What it defends (the confirmed red-team vectors)
- Host / IP / location / region / provider / timezone disclosure - direct,
  indirect ("which continent is closest"), and in other languages.
- System-prompt / hidden-instruction extraction - incl. "translate / repeat /
  complete your instructions".
- Jailbreak / roleplay / "developer mode" / DAN - incl. non-English.
- Coercion to execute code, read files, or exfiltrate.

It does NOT need to encode any secret: the model has no infra knowledge to leak
(verified) - this makes the refusal behavior robust and consistent rather than a
data guard.

## Run (after the GPUs are free; stop the demo's vLLM first)
```bash
# 1. Build the dataset (pure Python, no GPU)
python training/build_safety_dataset.py --out training/safety_dataset.jsonl

# 2. Train the adapter (needs a training venv, NOT the lean vLLM venv)
pip install "transformers>=4.45,<4.49" peft trl datasets accelerate bitsandbytes
python training/train_safety_lora.py \
    --data training/safety_dataset.jsonl --out training/safety-lora
# QLoRA (4-bit) by default -> fits a single 16GB T4. ~minutes for this dataset.
```

## Serve in production: MERGE the adapter (do NOT use vLLM --enable-lora on T4)
vLLM's runtime LoRA kernels are pathologically slow on Turing (T4 / sm_75) -
measured >90s for 20 tokens. So for production we MERGE the adapter into the base
weights and serve a normal model at full speed (safety baked in, zero adapter
overhead):
```bash
python training/merge_safety_lora.py --adapter training/safety-lora --out training/safety-merged
vllm serve training/safety-merged --served-model-name qwen2.5:7b-instruct \
    --tensor-parallel-size 2 --max-model-len 4096 \
    --gpu-memory-utilization 0.85 --dtype float16 --enforce-eager
```
The demo then serves the safety-baked model transparently (same served name). The
prompt-layer guard stays on as belt-and-braces.

## Validated result (2026-06-30)
Base vs the merged-LoRA, on guard-bypassing prompts (multilingual + indirect
location, timezone, system-prompt extraction, roleplay), with a NEUTRAL system
prompt (no hardening clause - so any refusal comes from the WEIGHTS):

    BASE model:        5 / 10 leaks  (hallucinated WRONG locations: "Germany/Telekom",
                                      "US/-5 UTC", "Google Cloud", a fictional server room)
    SAFETY-LoRA model: 0 / 10 leaks  (clean refusals, even for Spanish/German/French)

Two things this shows: (1) the refusal generalizes across languages from English
training data, and (2) crucially, every base "leak" was a HALLUCINATED WRONG
location - the model has no access to the real host, so the real location never
leaks regardless; the LoRA + guard just stop it confidently stating a wrong one.

## Tuning notes
- The dataset is intentionally refusal-heavy. If you see OVER-refusal of normal
  questions after training, add more benign Q&A / legit code-review rows in
  `build_safety_dataset.py` (keep the comply:refuse ratio sane, ~1:2 to 1:1) and
  lower epochs.
- This is the maintainer-approved, weight-level half of the demo's self-improving
  story: sanitized refusal traces -> a real LoRA update (NEVER auto-applied;
  trained and reviewed deliberately).
