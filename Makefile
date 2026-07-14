.PHONY: demo eval test lint verify

demo:
	PYTHONPATH=src python3 -m evidenceflow demo

eval:
	PYTHONPATH=src python3 -m evidenceflow eval --dataset evals/golden.jsonl

test:
	PYTHONPATH=src pytest

lint:
	ruff check .
	ruff format --check .

verify: lint test eval
