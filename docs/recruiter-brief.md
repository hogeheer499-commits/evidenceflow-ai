# Recruiter and interview brief

## Sixty-second explanation

The problem is that a useful enterprise AI workflow cannot blindly trust a
model or let it trigger an external action. Kleine Koe EvidenceFlow enforces an
expiring repository/check scope, runs allowlisted scanners without a shell in a
network-isolated process, preserves raw evidence and asks a local or
OpenAI-compatible model for a structured assessment. It independently validates
the response and every citation. A named human must approve the result before
the idempotent publisher can run. State survives restarts in SQLite and every
transition is written to a hash-chained audit log.

The regression suite proves the boundaries that matter: transient failures are
retried, ungrounded citations are rejected, approval cannot be bypassed,
duplicate runs do not duplicate the side effect, changed evidence cannot reuse
an existing case identifier, and audit tampering is detectable.

## Honest CV bullet

> Built a scope-enforced, approval-gated local AI assurance workflow with
> network-isolated scanner orchestration, SARIF normalization, grounded
> citations, durable state, idempotent exports, a loopback review console,
> tamper-evident auditing and automated regression evaluations.

After a public deployment, add only real measured outcomes, such as evaluated
case count, p95 latency, invalid-output rejection rate, and operational uptime.

## What the current numbers mean

- Thirty workflow, evaluation, assurance, persistence and web tests pass
  locally.
- The four-case synthetic golden set scores 100% risk accuracy and 100%
  citation validity with the deterministic provider.
- Local Ollama assurance runs with `qwen3.6:35b-a3b` converted five passing
  deterministic observations into assessments with five exact, resolvable
  citations and a private evidence pack. Observed model latency ranged from
  approximately 58 to 104 seconds. The final guarded repair-path run was low
  risk and took approximately 104 seconds; an earlier input/run was medium
  risk. A semantic validator rejects unsupported compliance, certification and
  completeness claims and permits only one bounded repair attempt.
- Those figures are regression evidence, not a claim of real-world model
  quality. A larger domain-labelled dataset is required before making an
  accuracy claim to an employer.
- A full deterministic pilot run executes repository policy, Semgrep, Gitleaks
  and offline OSV; external scanner processes are network-isolated and the
  lifecycle reaches one named, idempotent approved export.

## Design trade-offs to discuss

- Exact-quote grounding is explainable and deterministic but does not prove
  that a summary is semantically complete.
- SQLite is durable and reviewable for a single-node pilot; authenticated RBAC,
  PostgreSQL or a durable workflow engine is required for multi-user production
  use.
- Bounded retry handles transient provider failures but needs a queue/dead-
  letter strategy for asynchronous operation.
- Hash chaining detects modification but does not replace signed, access-
  controlled, append-only storage.
- Human approval reduces automation speed in exchange for a clear safety and
  accountability boundary.
