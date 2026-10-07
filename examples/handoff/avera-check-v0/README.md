# AVERA `avera.check/v0` handoff

This directory pins the first frozen external evidence envelope designed jointly
through [AVERA #12](https://github.com/mikheil-galoian/avera/issues/12) and
[CounterProof #81](https://github.com/hippoley/CounterProof/issues/81).

Upstream source pin:

- repository: `mikheil-galoian/avera`
- stable upstream tag: `v0.2.0`
- annotated tag resolves to commit:
  `348ea426d201596ed79046372098f7cc001e6682`
- implementation PR:
  [AVERA #14](https://github.com/mikheil-galoian/avera/pull/14)
- upstream spec:
  [AVERA_CHECK_EVIDENCE_V0.md](https://github.com/mikheil-galoian/avera/blob/v0.2.0/docs/AVERA_CHECK_EVIDENCE_V0.md)
- reproducible install target:
  `pip install "git+https://github.com/mikheil-galoian/avera@v0.2.0"`

The three files here are copied from AVERA's frozen example at the `v0.2.0` tag:

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
the integrity/binding rules of this experimental AVERA artifact from an
installable tagged upstream build.

The tag is a stable source reference, not a producer-authenticity claim; the
tag itself is not treated here as a signed attestation.

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
