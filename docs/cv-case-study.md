# CV case study — honest claims and proof plan

## What can be claimed now

> Built a scope-enforced, approval-gated local AI assurance workflow that
> runs Semgrep, Gitleaks and offline OSV in network-isolated processes,
> normalizes SARIF, validates grounded citations, persists review state, creates
> idempotent approved exports and records tamper-evident audit events.

Support that statement with the repository, architecture diagram, threat model,
tests and a short recorded demo. State clearly that current evaluations are
synthetic and that the project is not yet a production government deployment.

## Roles this demonstrates

- AI platform or LLM systems engineer;
- applied AI engineer for regulated environments;
- AI security / product security engineer;
- developer-platform or MLOps engineer;
- solutions architect for private AI.

The project is useful because it demonstrates engineering around the model:
scope enforcement, untrusted-input handling, deterministic validation,
idempotency, auditability, evaluation and product trade-offs. A large local
model by itself is not the portfolio differentiator.

## Evidence to add before stronger claims

1. Run a labelled evaluation on representative, authorized scanner results.
2. Record p50/p95 latency, invalid-output rate and reviewer agreement.
3. Demonstrate host-level egress monitoring for the separate local model
   process.
4. Add authenticated RBAC and signed/append-only evidence for a deployment.
5. Obtain an external maintainer review or a permissioned pilot reference.

Only after those steps should the CV mention real repository counts, measured
time saved, uptime, customer use or production deployment.
