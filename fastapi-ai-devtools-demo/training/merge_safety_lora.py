"""Merge the safety LoRA into the base weights -> a standalone model.

vLLM runtime LoRA (`--enable-lora`) is very slow on Turing (T4 / sm_75), so for
production the adapter is MERGED into the base weights. The result is a normal
model that vLLM serves at full speed with the safety behavior baked in - no
runtime adapter, no per-request LoRA overhead.

Run (CPU merge; needs ~30GB RAM, a few minutes; ~15GB output):
    python training/merge_safety_lora.py \
        --adapter training/safety-lora --out training/safety-merged

Serve the merged model with vLLM (the demo points OPENAI_MODEL at it):
    vllm serve training/safety-merged --served-model-name qwen2.5:7b-instruct \
        --tensor-parallel-size 2 --max-model-len 4096 \
        --gpu-memory-utilization 0.85 --dtype float16 --enforce-eager
"""

from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--adapter", default="training/safety-lora")
    ap.add_argument("--out", default="training/safety-merged")
    args = ap.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print("loading base (fp16, CPU) ...", flush=True)
    base = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.float16, device_map="cpu", low_cpu_mem_usage=True
    )
    print("applying + merging adapter ...", flush=True)
    model = PeftModel.from_pretrained(base, args.adapter)
    merged = model.merge_and_unload()
    print(f"saving merged model to {args.out} ...", flush=True)
    merged.save_pretrained(args.out, safe_serialization=True)
    AutoTokenizer.from_pretrained(args.base).save_pretrained(args.out)
    print("done: safety baked into the weights at", args.out)


if __name__ == "__main__":
    main()
