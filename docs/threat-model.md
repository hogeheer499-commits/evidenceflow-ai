# EvidenceFlow AI threat model

## Overview

EvidenceFlow is a Python reference workflow for converting supplied evidence
and normalized scanner observations into a structured assessment. Its primary
runtime surfaces are the CLI in `src/evidenceflow/cli.py`, the workflow state
machine in `src/evidenceflow/workflow.py`, model adapters in
`src/evidenceflow/providers.py`, validation in `src/evidenceflow/validation.py`,
the hash-chained audit log in `src/evidenceflow/audit.py`, the permissioned
assurance layer in `src/evidenceflow/assurance.py`, scanner sandboxing in
`src/evidenceflow/scanners.py`, durable pilot state in
`src/evidenceflow/persistence.py` and the loopback review console in
`src/evidenceflow/web.py`.

The current implementation is intended for local demonstrations and
single-node pilots. SQLite preserves workflow state across restarts and the
local publisher creates an idempotent approved export. It is not a multi-tenant
service, authorization server or append-only evidence store. The pilot CLI can
run read-only repository policy, Semgrep, Gitleaks and offline OSV checks or
import operator-supplied SARIF. Restricted external scanner processes run in a
Bubblewrap network namespace. The review console binds to loopback and requires
a CSRF token plus named approval before local export.

The assets that matter most are unpublished findings and source evidence,
scope authorization, assessment integrity, reviewer identity, model endpoint
configuration, audit continuity and the guarantee that an unapproved result
cannot cause an external action.

## Threat Model, Trust Boundaries, and Assumptions

### Trust boundaries

1. **Operator to scope policy.** The operator supplies a JSON scope manifest.
   `PilotScope` treats it as configuration and validates version, expiry,
   repository identifier, canonical checkout path, permitted checks and egress
   mode. The current file is not cryptographically signed; filesystem access is
   therefore an administrative trust assumption.
2. **Repository/scanner to EvidenceFlow.** Repository metadata, SARIF messages,
   paths, source text and case titles are untrusted data. They may contain
   malicious instructions, misleading severity, oversized content or markup.
   Deterministic scanner output remains evidence, not executable instruction.
3. **EvidenceFlow to model endpoint.** The model receives evidence and returns
   untrusted JSON. Restricted assurance scopes allow loopback model endpoints
   only. The model has no direct publisher or shell capability.
4. **Model output to domain model.** `OpenAICompatibleProvider` reconstructs
   typed domain objects. `validate_assessment` then requires a known risk value,
   bounded confidence and exact quotations resolving to supplied sources. One
   bounded repair attempt is permitted; persistent invalid output fails closed.
5. **Assessment to approved export.** `EvidenceWorkflow.publish` requires a
   named approval and uses an idempotency key. CLI and web review paths expose
   approval separately from the local directory export.
6. **Runtime to local artifacts.** Raw scan output, cases, assessments, evidence
   packs and JSONL audit events are written to an operator-selected directory.
   Hash chaining detects later modification but does not provide access control,
   confidentiality, signatures, trusted timestamps or durable append-only
   storage.

### Input control

- Attacker-controlled in a realistic repository-assurance scenario: checked-out
  repository names and files, dependency metadata, SARIF messages and paths,
  evidence text, and any indirect prompt-injection content embedded in them.
- Operator-controlled: scope files, repository checkout, output directory,
  model URL/model name/API key, reviewer name, retry policy and any supplied
  SARIF file. The local web dashboard operator also controls its loopback bind
  port and approved-export directory.
- Developer-controlled: code, default prompts, validation rules, packaging,
  test datasets and future publisher implementations.

### Security invariants

- No check may run unless repository identity, canonical path, check type and
  scope expiry are authorized.
- A `deny` or `local-only` scope must not send evidence to a non-loopback model
  endpoint.
- Model output is never authoritative evidence and cannot directly execute
  commands, open network connections beyond its configured completion request,
  publish findings or modify a repository.
- Every accepted citation must resolve exactly to supplied evidence.
- Invalid input or model output must fail closed.
- Publication requires a non-empty named reviewer and must remain idempotent.
- Reusing a case identifier with changed evidence must be rejected.
- Raw deterministic evidence must remain separately inspectable from AI prose.
- Audit records must reveal modification of the recorded hash chain.
- Restricted scanner processes must execute without network access and without
  shell interpolation.
- The review console must reject non-loopback binds and state-changing requests
  without its session CSRF token.

### Assumptions and exclusions

- The local operating system, Python runtime, checkout and scope file are under
  a trusted operator account. A host compromise defeats the current controls.
- Loopback inference is assumed to refer to a locally administered service. The
  code does not authenticate that service or encrypt loopback traffic.
- The built-in repository-policy scanner only checks file presence at standard
  locations. It does not prove policy quality or security compliance.
- SARIF severity is supplied by the originating tool and requires human review.
- Active exploitation, live production probing, autonomous patching, remote web
  access and multi-tenant use are outside the current product boundary.

## Attack Surface, Mitigations, and Attacker Stories

### Scope bypass and path confusion

An operator error or malicious manifest could attempt to scan an undeclared
checkout, invoke an unapproved check or use a repository identifier for output
path traversal. `PilotScope.authorize` compares resolved paths, enforces expiry
and an allowlist of checks, and restricts identifiers to letters, digits, dot,
underscore and hyphen. Scope files are not signed, so unauthorized filesystem
modification remains a material deployment risk.

### Data exfiltration

Sensitive evidence could leave through a hosted model endpoint, telemetry,
logs, browsing tools or future publishers. The assurance flow rejects non-
loopback model URLs for restricted scopes and emits no raw prompts as telemetry
attributes. Allowlisted external scanners run without a shell inside a
Bubblewrap network namespace. The model process is separate: production
deployment still needs host firewall or container egress enforcement because
URL validation alone is not a network sandbox.

### Prompt injection and deceptive evidence

A repository or SARIF message can tell the model to ignore its contract, invent
facts or request tool use. The model receives no shell or publisher tool, its
JSON is parsed into fixed fields, citations must quote supplied evidence, and a
human reviews the result. Exact-quote grounding proves provenance of the quote,
not correctness, completeness or semantic entailment. Reviewers must treat AI
summaries and patch suggestions as proposals.

### Malformed or resource-exhausting input

Evidence may be empty, duplicated or oversized. `validate_case` rejects those
conditions and caps total source text at 100,000 characters. SARIF import is
limited to 50 MB and 10,000 results. Model input is separately prioritized and
bounded to 100 observations and 90,000 observation characters; omitted items
remain in the raw report. Whole-file parsing can still briefly consume more
memory than the on-disk size, so a streaming parser is preferable for larger
production limits.

### Approval or replay bypass

An attacker may attempt to publish before approval, reuse a reviewer field, or
replay a prior case. The workflow state machine blocks publication outside the
approved state, requires a named reviewer, fingerprints case evidence and uses
an assessment-derived idempotency key. SQLite state survives restart and uses
immediate transactions for writes. It is still a single-node pilot store, not a
multi-tenant authorization boundary or distributed workflow engine.

### Local review console

The dashboard binds only to a loopback IP, escapes case fields, sends a strict
Content Security Policy and requires a per-process CSRF token for approval and
export. It has no user authentication and must not be exposed through a reverse
proxy or non-loopback tunnel. Anyone with access to the local browser session
can act as the operator and enter a reviewer name.

### Audit tampering and evidence-pack injection

Hash chaining detects modification, deletion or reordering only when the chain
is verified against a trusted starting point. It does not prevent replacement
of the entire file. Evidence packs neutralize triple-backtick sequences in raw
JSON before Markdown rendering, but they are not a safe HTML renderer. A real
deployment needs access-controlled append-only storage, signatures and
context-appropriate output encoding.

### Provider and dependency compromise

A malicious or compromised local model endpoint can return arbitrary content or
retain evidence. Independent validation, limited fields and human approval
reduce impact but cannot guarantee endpoint confidentiality. Python and optional
telemetry dependencies, local scanner binaries and their vulnerability databases
form a software-supply-chain boundary. Project-local OSV and Gitleaks installers
pin versions and SHA-256 digests; production should additionally verify release
provenance and use an approved update cadence.

## Severity Calibration (Critical, High, Medium, Low)

### Critical

- A path from attacker-controlled repository/SARIF content to arbitrary command
  execution on the assurance host without operator action.
- Bypassing the approval state to publish a false or secret finding to an
  external system, especially across multiple customers.
- Cross-tenant access to unpublished source code or findings in a future hosted
  deployment.

These require a deployed privileged surface that the current local CLI mostly
does not expose. A purely misleading model summary without a side effect is not
critical.

### High

- Restricted-scope evidence is transmitted to a non-local endpoint despite an
  egress-deny policy.
- A scope/path bypass scans a different sensitive checkout and includes its data
  in model input or artifacts.
- A future publisher duplicates or routes a private finding to the wrong
  organization because idempotency, tenancy or authorization is broken.
- Untrusted SARIF causes host file overwrite or code execution during import or
  evidence-pack generation.

### Medium

- Oversized SARIF reliably exhausts memory or disk in the pilot process.
- Audit records can be selectively modified without detection under the stated
  verification procedure.
- Invalid citations or a changed-evidence replay are accepted but no external
  action occurs.
- A misleading scanner severity or prompt injection survives into a private
  draft that a reviewer can still reject.

### Low

- Incorrect repository-policy presence results, formatting defects or missing
  metadata that affect one local report but do not expose data or bypass review.
- Telemetry counters are inaccurate without including raw evidence.
- A local demo artifact is duplicated in an operator-controlled output folder
  without crossing a trust boundary.

Developer-only test or documentation errors are low unless they alter shipped
security defaults or make unsupported production claims.
