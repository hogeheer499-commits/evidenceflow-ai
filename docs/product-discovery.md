# Product discovery — Local Government OSS Assurance Node

## Decision

Build and sell a narrow, permissioned assurance pilot before attempting a
multi-tenant platform. The first commercial product is not a vulnerability
scanner and not an "uncensored AI" appliance. It is a controlled workflow that
turns existing scanner evidence into reviewable, locally processed remediation
evidence.

The current EvidenceFlow core proves useful safety boundaries, but it does not
yet prove willingness to pay, production operations, or security accuracy on
real government repositories. Those are discovery and pilot outcomes.

## Ideal first customer

Primary buyer:

- a platform owner, OSPO lead or CISO delegate responsible for a Forgejo/Gitea
  environment with multiple repository owners;
- accountable for vulnerability governance, reusable CI controls or audit
  evidence;
- unable or unwilling to send source code and unpublished findings to an
  external model provider.

Likely users are platform engineers, application-security reviewers and
repository maintainers. Procurement, privacy, legal/CVD and enterprise
architecture are approval stakeholders.

The fastest route may be through an existing public-sector security or platform
supplier. A channel partner already has contractual access, liability cover and
procurement credibility; EvidenceFlow supplies the differentiated local
assurance workflow.

## Problem hypothesis

The buyer does not primarily lack scanners. The buyer has fragmented outputs,
duplicate findings, unclear ownership, inconsistent remediation evidence and a
privacy objection to cloud-based AI triage. Maintainers receive alerts but lack
a consistent path from raw evidence to a reviewed patch, test or exception.

This hypothesis must be validated in interviews. Public repositories and issue
backlogs show technical opportunity; they do not prove budget or buying intent.

## Paid discovery outcome

A two-to-four-week discovery should produce:

1. a signed scope manifest for 10–20 repositories and explicitly permitted
   checks;
2. a repository and data-flow threat model;
3. an inventory of existing scanners, formats, owners and ticketing routes;
4. an egress, retention, secrets and human-approval policy;
5. baseline measures for alert volume, duplication, triage time and closure;
6. a pilot architecture, acceptance tests, risk register and fixed-price plan.

Discovery is complete only when a named problem owner, budget owner,
operational owner and acceptable procurement route exist.

## Pilot hypothesis and success measures

Run only read-only checks against explicitly authorized checkouts or supplied
scanner output. Do not probe live production services.

Measure:

- percentage of ingested scanner results with preserved raw evidence;
- percentage of AI claims with resolvable citations;
- invalid model-output rejection rate;
- duplicate reduction and median human triage time;
- percentage of findings with a confirmed owner and disposition;
- number of accepted remediation tests or pull requests;
- external egress events, with a target of zero for local-only scopes;
- reviewer agreement on severity and usefulness.

The pilot is not successful merely because the model generates plausible
prose.

## Go/no-go gates

Proceed from discovery to pilot only if:

- the customer signs off the repository list, checks and data handling;
- at least one existing evidence source can be exported as SARIF, JSON or SBOM;
- a human review owner commits time to evaluate the output;
- a before/after metric is available;
- liability and disclosure responsibilities are assigned;
- there is a credible path to a paid rollout if acceptance criteria are met.

Do not build the full platform if interviews reveal that scanner aggregation is
already solved, cloud processing is acceptable, no owner will review findings,
or no procurement route exists.

## Product boundaries

In scope for the first pilot:

- local checkout authorization and scope enforcement;
- read-only repository-policy checks;
- import of supplied SARIF and later SBOM/OSV/secret-scanner output;
- local model triage with deterministic validation;
- private evidence packs and named human approval;
- audit and evaluation evidence.

Out of scope until separately contracted:

- active exploitation or production probing;
- autonomous publication, ticket creation or pull requests;
- claims of complete vulnerability or WCAG coverage;
- 24/7 SOC service, multi-tenant hosting or production SLA;
- legal conclusions about CRA, CVD or regulatory compliance.
