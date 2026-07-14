# Architecture and operating model

## Trust boundaries

The workflow treats both evidence and model output as untrusted input.

1. Input validation rejects missing identifiers, empty sources, duplicate
   source identifiers, and oversized evidence before any model call.
2. The provider returns a structured assessment, but the workflow reconstructs
   domain objects and validates them independently.
3. A citation is accepted only when its source exists and its exact quotation
   is present in that source.
4. No publisher receives data before a named reviewer approves the case.
5. The publisher receives a stable idempotency key derived from the case and
   assessment. Replaying the same workflow cannot repeat the side effect.

## Failure behavior

| Failure | Behavior | Audit event |
|---|---|---|
| invalid evidence | reject before model call | `input_rejected` |
| provider timeout/transient error | bounded exponential retry | `provider_retry` |
| malformed model response | one schema-repair attempt, then fail closed | `analysis_failed` |
| unverifiable citation | fail closed | `analysis_failed` |
| approval missing | publisher is not called | `publish_blocked` |
| duplicate publish | return prior receipt | `publish_deduplicated` |

## Observability

The core telemetry interface records counters and durations without requiring
an observability backend. Installing the `telemetry` extra enables
`OpenTelemetryTelemetry`, which uses the application's configured meter and
tracer providers. Useful production service-level indicators include:

- workflow completion and failure rate;
- provider latency and retry rate;
- invalid response and citation rejection rate;
- time waiting for approval;
- publish success and deduplication rate.

No prompt or raw evidence is emitted as a metric attribute.

## Deployment path

The reference implementation is deliberately transport-agnostic. A production
deployment can wrap it in FastAPI, a queue consumer, or a scheduled worker. The
state repository and publisher protocols are seams for PostgreSQL, durable
queues, ticketing systems, or compliance platforms. The in-memory adapters are
for tests and local demonstrations only.
