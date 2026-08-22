#!/bin/bash
set -e
REV=7442c03aeb0209ebdb7b03f60c9152316ee26955
M=/home/hoge-heer/d1-vision-lora/model
BASE=https://huggingface.co/unsloth/Qwen2.5-VL-3B-Instruct/resolve/$REV
for f in .gitattributes README.md added_tokens.json chat_template.jinja chat_template.json config.json generation_config.json merges.txt model.safetensors.index.json preprocessor_config.json special_tokens_map.json tokenizer.json tokenizer_config.json vocab.json; do
  curl -sfL --limit-rate 4M --retry 8 --retry-all-errors -o "$M/$f" "$BASE/$f"
done
echo "small files done"
for f in model-00001-of-00002.safetensors model-00002-of-00002.safetensors; do
  curl -sfL --limit-rate 4M --retry 20 --retry-all-errors --continue-at - -o "$M/$f" "$BASE/$f"
  echo "done $f"
done
echo "6b45c7afe391b4d9cc49f1ed3f6976f4a25ed40aa2165ed2ae118ff549355985  $M/model-00001-of-00002.safetensors" > /tmp/shards.sha
echo "d4578eeedb5bac3eab03fed443adbf31c3566bf02ba9ed185d0be0b0671c9550  $M/model-00002-of-00002.safetensors" >> /tmp/shards.sha
sha256sum -c /tmp/shards.sha && echo "MODEL VERIFIED rev $REV"
