"""Fine-tune a SAFETY LoRA adapter for the demo's GPU model (bakes refusals into
the weights, on top of the prompt-layer guard).

Trains a small LoRA adapter on Qwen/Qwen2.5-7B-Instruct from the messages-format
dataset built by build_safety_dataset.py, so the served model intrinsically
refuses host/location disclosure, system-prompt extraction, jailbreaks, and
code-execution coercion - including paraphrases and other languages that slip a
regex guard - while still doing normal Q&A and code review.

REQUIREMENTS (NOT installed in the lean vLLM venv - install into a training venv):
    pip install "transformers>=4.45,<4.49" peft trl datasets accelerate bitsandbytes
A single 16GB GPU (T4) is enough with 4-bit (QLoRA) loading (default here).

RUN (after the GPUs are free; the demo's vLLM must be stopped first):
    python training/build_safety_dataset.py --out training/safety_dataset.jsonl
    python training/train_safety_lora.py \
        --data training/safety_dataset.jsonl --out training/safety-lora

SERVE the adapter with vLLM (the demo then points OPENAI_MODEL at "safety"):
    vllm serve Qwen/Qwen2.5-7B-Instruct --enable-lora \
        --lora-modules safety=training/safety-lora \
        --served-model-name qwen2.5:7b-instruct --tensor-parallel-size 2 ...
    # then request model "safety" (or alias the served name to it).

This is a SHOWCASE of the demo's "AI-First / self-hosted, self-improving" story:
the operator-approved safety traces become a real weight update, not just a prompt.
"""

from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen2.5-7B-Instruct")
    ap.add_argument("--data", default="training/safety_dataset.jsonl")
    ap.add_argument("--out", default="training/safety-lora")
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1024)
    ap.add_argument("--no-4bit", action="store_true", help="disable 4-bit/QLoRA")
    args = ap.parse_args()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    quant = None
    if not args.no_4bit:
        from transformers import BitsAndBytesConfig

        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=quant,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    # LoRA on all attention + MLP projections (standard for Qwen2.5).
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    dataset = load_dataset("json", data_files=args.data, split="train")

    # Render each messages-format row to a single training string via the model's
    # chat template (explicit, so we don't depend on TRL's format auto-detection).
    def _to_text(ex):
        return {
            "text": tokenizer.apply_chat_template(ex["messages"], tokenize=False)
        }

    dataset = dataset.map(_to_text, remove_columns=dataset.column_names)

    sft_config = SFTConfig(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        max_seq_length=args.max_len,
        logging_steps=10,
        save_strategy="epoch",
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        bf16=False,
        fp16=True,
        gradient_checkpointing=True,
        report_to=[],
        dataset_text_field="text",
        packing=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset,
        peft_config=peft_config,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"Saved safety LoRA adapter to {args.out}")


if __name__ == "__main__":
    main()
