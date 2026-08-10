# Statement of work template — Permissioned OSS Assurance Pilot

## Parties and purpose

This statement of work is between `[customer]` and **Kleine Koe**. The purpose
is to evaluate a local assurance workflow on an explicitly authorized set of
repositories. It does not authorize testing of production services.

## Scope

- Engagement ID: `[id]`
- Repositories: `[attach signed manifest]`
- Checks: `[repository policy / supplied SARIF / Semgrep / Gitleaks / offline OSV]`
- Deployment: `[customer-controlled / single-tenant Kleine Koe appliance]`
- Model: `[local model and version]`
- Duration: `[4–8 weeks]`

Changes to repositories, checks, data handling or external actions require a
written scope amendment.

## Deliverables

1. Hardened pilot configuration and signed-off scope.
2. Preserved raw scanner results and normalized observations.
3. Local AI-assisted triage with grounded citations.
4. Named human review and approval workflow.
5. Private evidence packs and management summaries.
6. Metrics report, limitations and rollout recommendation.
7. Knowledge transfer and operational handoff.

## Acceptance criteria

- 100% of executed checks are within the approved manifest;
- restricted scanners run with enforced network isolation;
- raw scanner evidence is preserved separately from AI output;
- invalid or ungrounded model output fails closed;
- no approved external export occurs without a named reviewer;
- audit-chain verification passes for delivered pilot events;
- customer reviewers score usefulness and severity agreement against the agreed
  baseline;
- zero unapproved production probes or external data-egress events.

Customer-specific targets for time saved, duplicate reduction and remediation
acceptance must be added after discovery.

## Commercials

Fixed pilot fee: `[€45,000–€90,000 excluding VAT]`  
Milestones: `[scope / working integration / evaluated pilot / handoff]`  
Expenses and third-party licenses: `[included / excluded]`

## Security and disclosure

Kleine Koe will treat source code and unpublished findings as confidential.
Suspected vulnerabilities remain private and follow the customer’s coordinated
disclosure route. Commercial follow-up is never a condition of correct
disclosure.

## Explicit limitations

The pilot does not prove complete vulnerability coverage, legal compliance or
future absence of vulnerabilities. AI output is advisory until a qualified
reviewer accepts it.

This template requires legal, tax, insurance and procurement review before
signature.
