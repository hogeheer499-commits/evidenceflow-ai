# Pilot operations runbook

## Before an engagement

1. Assign an engagement ID and named Kleine Koe operator.
2. Obtain written repository/check authorization and expiry date.
3. Confirm data classification, retention, egress and disclosure contacts.
4. Create a dedicated OS account or isolated host for the engagement.
5. Install pinned scanners and refresh the OSV database while internet access is
   deliberately enabled.
6. Disable general egress before customer evidence is introduced.
7. Verify backups, disk encryption, time synchronization and log destination.
8. Run `evidenceflow preflight` and archive the output.

## Run a pilot scan

```bash
PYTHONPATH=src python3 -m evidenceflow pilot \
  --scope customer-scope.json \
  --repo /authorized/checkout \
  --repo-id authorized-id \
  --checks repository-policy semgrep gitleaks osv \
  --offline-db .tools/osv-cache \
  --output-dir /protected/engagement-artifacts
```

For local Qwen, configure a loopback endpoint and a bounded timeout/token budget.
Do not enable browsing or attach shell tools to the model process.

## Review

1. Confirm the audit chain is valid.
2. Compare AI claims with raw evidence and source locations.
3. Validate reachability and severity manually.
4. Assign an owner and disposition.
5. Approve with a named reviewer only when the evidence is sufficient.
6. Export locally; move the artifact through the customer-approved channel.

## Incident conditions

Stop processing and preserve evidence when:

- a check runs outside scope;
- restricted evidence attempts external egress;
- a secret appears in logs or an unintended output;
- audit verification fails;
- scanner or model output causes unexpected file or process activity;
- customer authority or scope is disputed.

Notify the engagement security contact. Do not publish or independently contact
third parties unless the agreed incident/CVD route requires it.

## Closeout

- deliver only approved artifacts;
- obtain disposition for residual copies and backups;
- revoke credentials and remove checkouts on schedule;
- record metrics, exceptions and lessons learned;
- do not reuse customer evidence in demos or model evaluation without separate
  written permission.
