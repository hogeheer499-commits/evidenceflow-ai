# Recruiter and interview brief

## Sixty-second explanation

The problem is that a useful enterprise AI workflow cannot blindly trust a
model or let it trigger an external action. EvidenceFlow accepts operational
evidence, validates it, asks a local or OpenAI-compatible model for a structured
assessment, and then independently validates the response and every citation.
It fails closed on invalid output. A named human must approve the result before
the idempotent publisher can run. Every transition is written to a hash-chained
audit log, and counters and latency measurements can be mirrored to
OpenTelemetry.

The regression suite proves the boundaries that matter: transient failures are
retried, ungrounded citations are rejected, approval cannot be bypassed,
duplicate runs do not duplicate the side effect, changed evidence cannot reuse
an existing case identifier, and audit tampering is detectable.

## Honest CV bullet

> Built an approval-gated AI evidence-triage workflow with local/OpenAI-
> compatible inference, grounded citations, bounded retries, idempotent side
> effects, tamper-evident auditing, OpenTelemetry instrumentation, and automated
> regression evals.

After a public deployment, add only real measured outcomes, such as evaluated
case count, p95 latency, invalid-output rejection rate, and operational uptime.

## What the current numbers mean

- Nine workflow/evaluation tests pass locally.
- The four-case synthetic golden set scores 100% risk accuracy and 100%
  citation validity with the deterministic provider.
- A real local Ollama smoke test with `qwen2.5-coder:7b` exercised the
  OpenAI-compatible transport and produced a schema-valid, grounded citation
  after the bounded repair path was added.
- Those figures are regression evidence, not a claim of real-world model
  quality. A larger domain-labelled dataset is required before making an
  accuracy claim to an employer.

## Design trade-offs to discuss

- Exact-quote grounding is explainable and deterministic but does not prove
  that a summary is semantically complete.
- In-memory state is ideal for a small reference implementation; PostgreSQL or
  a durable workflow engine is required for multi-worker production use.
- Bounded retry handles transient provider failures but needs a queue/dead-
  letter strategy for asynchronous operation.
- Hash chaining detects modification but does not replace signed, access-
  controlled, append-only storage.
- Human approval reduces automation speed in exchange for a clear safety and
  accountability boundary.
