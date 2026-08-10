# Release and customer-pilot checklist

## Code release

- [x] `make verify` passes in the release worktree.
- [x] Full pilot smoke test passes with pinned scanners and offline OSV data.
- [x] Local model smoke test passes and deterministic fallback is documented.
- [x] Threat model and `SECURITY.md` match the release surfaces.
- [x] Version and changelog are current.
- [x] No artifacts, databases, model output, customer data or `.tools` binaries
      are committed.
- [x] Git diff is reviewed for secrets and generated files.
- [x] Scanner release digests are revalidated against official releases.
- [ ] GitHub branch protection and private vulnerability reporting are enabled.

## Before offering a pilot

- [ ] Kleine Koe legal entity, VAT, insurance and contracting details are added
      to approved templates.
- [ ] Professional and cyber-liability cover matches the engagement.
- [ ] Customer procurement route and security contact are confirmed.
- [ ] Scope, retention, egress, incident and CVD terms are signed.
- [ ] Dedicated encrypted environment and backups are prepared.
- [ ] Reviewer capacity and acceptance metrics are committed.
- [ ] Customer-approved transfer channel exists for final artifacts.

## Before claiming production readiness

- [ ] Authenticated identity and RBAC replace the loopback trust assumption.
- [ ] PostgreSQL/durable workflow and protected object storage replace local
      single-node state.
- [ ] Signed append-only audit receipts and trusted timestamps are implemented.
- [ ] Host-level egress enforcement covers model and scanner processes.
- [ ] Multi-customer isolation and deletion are independently tested.
- [ ] Representative labelled evaluation and external security review exist.
- [ ] Monitoring, recovery, support and incident SLAs are operational.
