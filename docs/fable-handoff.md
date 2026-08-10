# EvidenceFlow handoff for independent review and learning

## Purpose

This document gives an independent reviewer enough context to reproduce the
current single-node pilot, teach it module by module and design one real but
permissioned use case. It deliberately separates repository evidence from
commercial claims.

EvidenceFlow is a working prototype. It is not a multi-tenant service, a
compliance product, a penetration test or evidence that a customer saves time.

## Clean-room reproduction

Use Python 3.12 and `uv`. Do not reuse the developer's ignored `artifacts/` or
`.tools/` directories when judging reproducibility.

```bash
git clone --branch agent/publish-evidenceflow-pilot \
  https://github.com/hogeheer499-commits/evidenceflow-ai.git
cd evidenceflow-ai
uv sync --extra dev
make verify
```

The review branch is published in draft PR
https://github.com/hogeheer499-commits/evidenceflow-ai/pull/1. After that PR is
reviewed and merged, the explicit `--branch` argument can be omitted.

Expected regression evidence at this release:

- Ruff lint and formatting checks pass;
- 30 Pytest tests pass;
- the four-case synthetic evaluation reports risk accuracy `1.0` and citation
  validity `1.0`;
- the evaluation explicitly states that it is not an enterprise benchmark.

To exercise the permissioned deterministic scanner path:

```bash
make install-scanners
make update-osv-db
make preflight
make pilot
```

The pilot must stop in `pending_approval`. Approval and export are separate
commands and require a named human reviewer.

`make preflight` now performs an operational Bubblewrap network-isolation smoke
test. The 4 August Codex container had the binary and all three scanners but
denied the required network namespace operation (`RTM_NEWADDR: Operation not
permitted`); the complete scanner pilot therefore correctly remained blocked
there. Re-run this step on the clean Linux review host. Do not weaken isolation
to make the test pass.

The GitHub Actions assurance job deliberately runs `make pilot-policy`, not the
external scanners, because GitHub-hosted runners enforce the same namespace
restriction. That green job proves the state-machine and audit smoke path only.
Treat a compatible-host `make pilot` receipt as separately required evidence.

## What to teach, in order

1. **Data contract** — `src/evidenceflow/models.py`: evidence cases,
   assessments, citations and workflow states.
2. **Trust boundary** — `src/evidenceflow/validation.py`: why valid JSON is not
   trusted, how exact citations resolve and which assurance claims are blocked.
3. **Model adapter** — `src/evidenceflow/providers.py`: local endpoint policy,
   bounded transport retries and one repair attempt.
4. **State machine** — `src/evidenceflow/workflow.py`: fail-closed analysis,
   retry of failed work, named approval and idempotent publication.
5. **Scanner boundary** — `src/evidenceflow/scanners.py`: fixed executable and
   argument allowlists, SARIF and optional network isolation.
6. **Pilot orchestration** — `src/evidenceflow/assurance.py`: signed scope,
   preserved evidence, bounded model input and generated evidence packs.
7. **Durability** — `src/evidenceflow/persistence.py`: SQLite state and restart
   behavior.
8. **Human review** — `src/evidenceflow/web.py`: loopback-only console, CSRF
   token and separate approve/export transitions.
9. **Audit and reporting** — `src/evidenceflow/audit.py` and
   `src/evidenceflow/reporting.py`: hash chaining, metrics and management
   summaries.
10. **Limits** — `docs/threat-model.md` and `README.md`: what the prototype
    explicitly does not prove.

The learner should be able to explain each boundary without slides before
representing the product to a customer.

## Six-week practical learning path

### Week 1 — reproduce and narrate

- clone into a clean directory;
- run `make verify`;
- trace one synthetic case from input through pending approval;
- explain why the model cannot publish anything;
- intentionally break a citation and observe fail-closed behavior.

Exit criterion: the operator can draw the architecture and explain every
trust boundary in plain Dutch.

### Week 2 — operate the deterministic pilot

- install the pinned scanners and offline OSV database;
- inspect the example scope;
- run the full local pilot;
- inspect raw SARIF, normalized observations, the evidence case, assessment,
  audit chain and management summary;
- approve and export once, then prove duplicate publication is prevented.

Exit criterion: the operator can distinguish scanner fact, model proposal,
human decision and exported claim.

### Week 3 — design the handoff reliability use case

- use only Watermelon's public documentation and an environment owned by the
  operator;
- define one synthetic agent, two test channels, business-hours behavior and
  expected inbox destination;
- write explicit pass/fail criteria for trigger, visible user message, actual
  inbox arrival, timestamps and ownership;
- do not access or test Watermelon or a customer tenant without written
  authorization.

Exit criterion: a signed test plan exists with no production access and no
unsupported claim about Watermelon.

### Week 4 — build the adapter outside the core

- create a small adapter that turns owned test results into EvidenceFlow source
  records;
- preserve screenshots or API receipts without secrets;
- keep the product-specific adapter separate from the generic workflow;
- add deterministic tests for missing handoff, wrong destination, delay and
  outside-hours behavior.

Exit criterion: the owned test flow produces a reviewable pending assessment.

### Week 5 — reviewer exercise and measurement

- have a second person review the assessment;
- measure preparation time, model corrections, missing evidence and reviewer
  changes;
- reject at least one deliberately unsupported conclusion;
- export only an approved synthetic evidence pack.

Exit criterion: the measurement sheet contains facts rather than claimed ROI.

### Week 6 — commercial readiness decision

- write a one-page case using only measured results;
- remove any claim the exercise did not prove;
- decide whether a paid discovery is justified;
- prepare a customer scope with explicit authorization, data minimization,
  acceptance criteria and a stop rule.

Exit criterion: the seller can demo, operate and explain the workflow and can
answer what happens when the model is wrong.

## Watermelon-specific boundary

Watermelon's public documentation states that handoff works only in a live
agent environment, varies around business hours and channels, and can show a
handoff response while no conversation appears in the inbox when configuration
or triggers are wrong. That is a valid public test hypothesis, not evidence
that Watermelon's internal QA is inadequate.

The first owned-environment demonstrator should verify:

| Check | Evidence |
|---|---|
| Trigger recognized | exact synthetic user message and configuration version |
| User sees correct status | captured UI output with timestamp |
| Handoff really occurs | inbox receipt with matching synthetic correlation ID |
| Destination is correct | team/person identifier from the owned test setup |
| Outside-hours rule holds | configuration plus observed result |
| Human takes ownership | named synthetic reviewer action |

## Claims allowed after reproduction

Allowed:

- “We built and reproduced a local, approval-gated evidence workflow.”
- “The current synthetic regression suite passes 30 tests and four evaluation
  cases.”
- “A human must approve before the local exporter runs.”

Not allowed without a customer measurement:

- time or cost savings;
- enterprise accuracy, security completeness or compliance;
- a working Watermelon integration;
- production readiness, SLA or multi-tenant isolation;
- proof that any prospect has the hypothesized problem.

## Reviewer output requested

Return:

1. clean-checkout test results and environment versions;
2. discrepancies between documentation and observed behavior;
3. a plain-language explanation suitable for the seller;
4. the owned-environment handoff test plan;
5. code or scope changes required before customer data;
6. a go/no-go decision for a paid discovery.
