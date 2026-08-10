# Pilot offer and sales pitch

> **Commercial status — 4 August 2026:** the bands below are future enterprise
> packaging hypotheses, not the current cold-outreach offer and not validated
> pricing. KleineKoe's current first paid step is a two-working-day evidence
> discovery for €950, without customer data or environment access, ending in a
> go/no-go and case-specific estimate. Do not send or quote the enterprise
> bands until a real buyer, procurement route and delivery scope justify them.

## Offer ladder

### 1. Sovereign OSS assurance discovery — €15k–€30k

Use this only after the €950 problem/fit discovery proves that a larger,
procurement-bearing enterprise discovery is needed. It is not the first cold
outreach transaction.

Deliverables:

- stakeholder and workflow interviews;
- signed repository/check scope;
- threat model and data-flow/egress assessment;
- scanner, ownership and integration inventory;
- baseline measures and acceptance criteria;
- fixed-price pilot design and implementation backlog.

Commercial promise: eliminate uncertainty before either party commits to an
integration project. Do not promise vulnerability reduction yet.

### 2. Permissioned assurance pilot — €45k–€90k

Scope: 10–20 explicitly authorized repositories, four to eight weeks, one local
deployment and a limited set of scanner feeds.

Deliverables:

- deterministic repository-policy and supplied SARIF/SBOM ingestion;
- local AI triage with citation and schema validation;
- ownership, remediation-test and patch suggestions for human review;
- private evidence packs and auditable approval records;
- measured before/after results and a rollout recommendation.

Exclude active production testing, autonomous external actions, 24/7 service
and compliance certification.

### 3. Platform rollout — €150k–€350k

Sell only after the pilot meets its acceptance criteria. A rollout may add
Forgejo events, durable state, customer identity/RBAC, queueing, secrets
management, signed artifacts, multi-team onboarding, observability and support.

The Beelink is a development or single-tenant pilot node. Production pricing
must include redundant infrastructure, operational ownership, liability,
support and the applicable procurement route.

## Thirty-second pitch

> Jullie hebben waarschijnlijk al scanners. Het probleem is dat de uitkomsten
> verspreid zijn, onderhouders dezelfde meldingen opnieuw moeten beoordelen en
> gevoelige broncode of nog niet gepubliceerde kwetsbaarheden niet zomaar naar
> een cloudmodel mogen. EvidenceFlow verwerkt bestaande scannerbewijzen lokaal,
> laat AI alleen triëren en herstel voorstellen, controleert iedere claim tegen
> de bron en vereist menselijke goedkeuring. We beginnen met 10–20 toegestane
> repositories en bewijzen binnen de pilot of triagetijd daalt en auditbewijs
> verbetert—zonder productieprobe en zonder externe data-egress.

## First-contact email

Subject: `Kleine lokale assurance-pilot voor Forgejo-repositories`

> Beste [naam],
>
> Bij publieke codeplatforms ligt de uitdaging vaak niet in nóg een scanner,
> maar in het samenbrengen van scannerbewijs, eigenaarschap, menselijke triage
> en reproduceerbare herstelbesluiten. Wij bouwen een lokale, evidence-first
> workflow: bestaande SARIF/SBOM-resultaten blijven de feitenbron; een lokaal
> model helpt alleen met deduplicatie, context en herstelvoorstellen; iedere
> externe actie blijft approval-gated.
>
> Ik wil graag in 30 minuten toetsen of dit aansluit op jullie Forgejo/Gitea-
> workflow. Als dat zo is, stellen we een afgebakende discovery voor met een
> expliciete repo- en datascope. Er wordt niet actief op productie getest.
>
> Ik kan vooraf een éénpagina-architectuur en een synthetisch evidence pack
> toesturen. Wie beheert bij jullie scannertriage en repository-governance?

## Discovery call

Ask before demonstrating:

1. Which scanners and formats already exist, and who reviews their output?
2. Where do duplicate, stale or unowned findings currently accumulate?
3. Which evidence is too sensitive for an external AI provider?
4. What must a reviewer see before accepting a patch or exception?
5. Which 10–20 repositories could be explicitly authorized for a pilot?
6. Which measured outcome would unlock budget for rollout?
7. Which framework agreement, innovation budget or incumbent supplier can carry
   the work?

End the call with a concrete next artifact: scope workshop, evidence sample or
procurement introduction. Do not lead with model size, "uncensored" behavior or
an unsolicited vulnerability.

## Objection handling

"We already have security scanners."

> Good—the pilot consumes their evidence. We test whether local triage,
> ownership and evidence packs reduce the manual gap after scanning.

"We cannot let AI see our findings."

> That is the design constraint: a local endpoint, deny-by-default egress,
> preserved raw evidence and no autonomous publication.

"Open source maintainers can do this themselves."

> Individual fixes are not the paid value. The value is a repeatable workflow
> across teams with measurable review, provenance and operational ownership.

"Can you guarantee that all vulnerabilities are found?"

> No. We contract for defined coverage, evidence handling and workflow outcomes,
> not impossible completeness. Deterministic scanners and human validation
> remain authoritative.

## What must be proven before quoting the upper bands

- a real problem owner confirms the pain;
- pilot repositories and evidence are authorized in writing;
- measurable baseline and acceptance criteria exist;
- the team can explain false positives, missed findings and model limitations;
- secure operations, liability and disclosure handling are credible;
- the buyer has a valid procurement route.

The price bands are packaging hypotheses, not evidence that a particular
government organization has approved this budget.
