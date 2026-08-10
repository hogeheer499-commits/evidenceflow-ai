.PHONY: demo eval test lint verify install-scanners update-osv-db preflight pilot pilot-policy

UV ?= uv

demo:
	PYTHONPATH=src $(UV) run python -m evidenceflow demo

eval:
	PYTHONPATH=src $(UV) run python -m evidenceflow eval --dataset evals/golden.jsonl

test:
	PYTHONPATH=src $(UV) run --extra dev pytest

lint:
	$(UV) run --extra dev ruff check .
	$(UV) run --extra dev ruff format --check .

verify: lint test eval

install-scanners:
	./scripts/install-scanners.sh

update-osv-db:
	./scripts/update-osv-database.sh

preflight:
	PYTHONPATH=src python3 -m evidenceflow preflight

pilot:
	PYTHONPATH=src python3 -m evidenceflow pilot --scope examples/pilot-scope.json --repo . --repo-id evidenceflow-ai --checks repository-policy semgrep gitleaks osv --offline-db .tools/osv-cache --output-dir artifacts/pilot

pilot-policy:
	PYTHONPATH=src python3 -m evidenceflow pilot --scope examples/pilot-scope.json --repo . --repo-id evidenceflow-ai --checks repository-policy --output-dir artifacts/pilot
