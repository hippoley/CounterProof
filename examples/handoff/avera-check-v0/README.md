# AVERA `avera.check/v0` handoff

This directory pins the first frozen external evidence envelope designed jointly
through [AVERA #12](https://github.com/mikheil-galoian/avera/issues/12) and
[CounterProof #81](https://github.com/hippoley/CounterProof/issues/81).

Upstream source pin:

- repository: `mikheil-galoian/avera`
- upstream main commit containing the v0 contract:
  `c5f2c43e4dd67617db430978870bd7013a8777e9`
- implementation PR:
  [AVERA #14](https://github.com/mikheil-galoian/avera/pull/14)
- upstream spec:
  [AVERA_CHECK_EVIDENCE_V0.md](https://github.com/mikheil-galoian/avera/blob/c5f2c43e4dd67617db430978870bd7013a8777e9/docs/AVERA_CHECK_EVIDENCE_V0.md)

The three files here are copied from AVERA's frozen example at that contract:

- `baseline.xml`
- `current.xml`
- `envelope.json`

CounterProof independently checks:

```text
schema = avera.check/v0
producer = avera
        ↓
AVERA v0 canonical JSON digest
        ↓
published envelope digest matches
        ↓
baseline.xml SHA-256 matches envelope
current.xml SHA-256 matches envelope
```

## Boundary

A successful handoff establishes only that CounterProof can consume and verify
the integrity/binding rules of this experimental AVERA artifact.

It does **not** establish:

- that the JUnit reports identify the source-code candidates that produced them;
- that AVERA's `confirmed_regression` means CounterProof `WITNESSED`,
  `CONTRADICTED`, or `PROVEN`;
- that the digest authenticates the producer;
- that a merge should be allowed or blocked.

The intended composition remains:

```text
AVERA
baseline PASS → current FAIL
        ↓
avera.check/v0 external evidence
        ↓
CounterProof attaches it to a separately candidate-bound claim
        ↓
CounterProof performs its own replay / oracle / scope reasoning
        ↓
human reviewer keeps merge authority
```

No AVERA-specific adapter protocol or new CounterProof packet type is introduced.
