# Data-processing schedule template

This is an engineering checklist, not legal advice. A qualified reviewer must
adapt it to the contract and applicable privacy law.

## Processing

- Controller/customer: `[name]`
- Processor/service provider: `Kleine Koe / legal entity details`
- Purpose: permissioned software-assurance pilot
- Duration: `[dates and retention period]`
- Data subjects: `[if any; avoid personal data where possible]`
- Data types: source code, scanner output, repository metadata, reviewer identity
- Special-category data: not expected; stop and notify if encountered

## Architecture commitments

- deployment location: `[customer / single-tenant appliance]`
- model endpoint: `[loopback/local endpoint]`
- external egress: `[deny/local-only policy]`
- encryption at rest/in transit: `[implementation]`
- authorized personnel: `[roles and names/process]`
- sub-processors: `[none / list]`
- backups and recovery: `[policy]`
- deletion/return: `[schedule and evidence]`

## Security controls

- signed scope manifest and least-privilege access;
- network-isolated scanner processes;
- secrets excluded from metrics and ordinary logs;
- fail-closed model-output validation;
- named approval for consequential exports;
- tamper-evident audit chain plus protected storage;
- incident and vulnerability-disclosure routes;
- periodic access and retention review.

## Customer decisions required

- lawful basis and necessity;
- whether a DPIA is required;
- permitted evidence sources and repository owners;
- international transfer position;
- breach-notification contacts and timing;
- retention, litigation hold and deletion evidence.
