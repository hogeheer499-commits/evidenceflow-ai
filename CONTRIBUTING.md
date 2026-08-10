# Contributing

EvidenceFlow accepts focused improvements that preserve its core invariants:
scope before scanning, deterministic evidence before AI prose, fail-closed
validation and named approval before export.

## Development

```bash
python3 -m pip install -e '.[dev]'
make verify
```

For scanner changes, install the pinned local tools and run `make pilot`. Do not
commit `.tools/`, `artifacts/`, scanner output, local databases or model output.

## Pull requests

- explain the trust boundary or product behavior being changed;
- add tests for failure as well as success;
- update the threat model when a new input, side effect, network path or
  privilege is introduced;
- avoid new runtime dependencies unless the benefit and supply-chain cost are
  clear;
- use synthetic evidence only;
- keep external actions disabled by default.

Security reports do not belong in public issues. Follow `SECURITY.md`.
