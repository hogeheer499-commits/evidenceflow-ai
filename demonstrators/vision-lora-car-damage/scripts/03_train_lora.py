#!/usr/bin/env python3
"""LoRA fine-tune of Qwen2.5-VL-3B-Instruct on the train split (Unsloth, ROCm).

Usage: 03_train_lora.py --base <model> --manifest manifest.csv --data-root <dir>
                        --out <adapter_dir> [--epochs 2]
Single pre-registered configuration; no hyper-parameter search.
"""
import argparse, csv, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import torch
from PIL import Image
from unsloth import FastVisionModel
from unsloth.trainer import UnslothVisionDataCollator
from trl import SFTTrainer, SFTConfig
from common import PROMPT, target_text

MAX_PIXELS = 512 * 512
MIN_PIXELS = 128 * 128

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    args = ap.parse_args()

    model, tokenizer = FastVisionModel.from_pretrained(
        args.base, load_in_4bit=False, dtype=torch.bfloat16,
        use_gradient_checkpointing="unsloth")
    tokenizer.image_processor.max_pixels = MAX_PIXELS
    tokenizer.image_processor.min_pixels = MIN_PIXELS
    model = FastVisionModel.get_peft_model(
        model, finetune_vision_layers=True, finetune_language_layers=True,
        finetune_attention_modules=True, finetune_mlp_modules=True,
        r=args.rank, lora_alpha=args.rank, lora_dropout=0, bias="none",
        random_state=42, use_rslora=False)

    rows = [r for r in csv.DictReader(open(args.manifest)) if r["split"] == "train"]
    def to_sample(r):
        img = Image.open(os.path.join(args.data_root, r["path"])).convert("RGB")
        return {"messages": [
            {"role": "user", "content": [{"type": "image", "image": img},
                                         {"type": "text", "text": PROMPT}]},
            {"role": "assistant", "content": [{"type": "text", "text": target_text(r["label"])}]}]}
    dataset = [to_sample(r) for r in rows]
    print(f"train samples: {len(dataset)}")

    FastVisionModel.for_training(model)
    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer,
        data_collator=UnslothVisionDataCollator(model, tokenizer),
        train_dataset=dataset,
        args=SFTConfig(
            per_device_train_batch_size=2, gradient_accumulation_steps=4,
            warmup_steps=10, num_train_epochs=args.epochs, learning_rate=args.lr,
            bf16=True, fp16=False, logging_steps=10, optim="adamw_torch",
            weight_decay=0.01, lr_scheduler_type="linear", seed=42,
            output_dir=args.out + "-trainer", report_to="none",
            remove_unused_columns=False, dataset_text_field="",
            dataset_kwargs={"skip_prepare_dataset": True},
            max_seq_length=1024, save_strategy="no"))
    t0 = time.time()
    stats = trainer.train()
    elapsed = time.time() - t0
    os.makedirs(args.out, exist_ok=True)
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    trainer.state.save_to_json(os.path.join(args.out, "trainer_state.json"))
    with open(os.path.join(args.out, "train_summary.json"), "w") as f:
        json.dump({"train_samples": len(dataset), "epochs": args.epochs,
                   "lr": args.lr, "rank": args.rank, "elapsed_s": elapsed,
                   "metrics": stats.metrics,
                   "max_memory_reserved_gb": torch.cuda.max_memory_reserved() / 1e9},
                  f, indent=2)
    print(f"TRAIN DONE in {elapsed/60:.1f} min; metrics={stats.metrics}")

if __name__ == "__main__":
    main()
