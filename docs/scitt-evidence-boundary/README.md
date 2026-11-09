# SCITT Evidence Boundary Lab — v0.1 (experimental)

**Maintainer:** Noah Ellis ([@hippoley](https://github.com/hippoley))  
**Status:** Public, revision-pinnable **illustrative negative-test fixture**. **Not real hardware evidence, not a second implementation, not SCITT conformance certification, not endorsed by IETF, Nicholas Templeman, Joel Hillier, CSOAI, or Certisyn.**

## What this adds

A small *consumer-side* assertion checker for a high-risk category error: **a correct signature, a matching digest, or actuator ACK must not be silently promoted to independent physical-effect evidence.** The cases are intentionally synthetic; the verifier tests *claim discipline* only. No original WindowPilot code, hardware observations, private tokens or signed payloads are included.

This is a public artifact to inspect without access to the private [WindowPilot repository](https://github.com/hippoley/WindowPilot). It does **not** solve the private-PR #47 accessibility issue by exposing its contents; it provides a separate, explicitly limited artifact.

## Exact upstream references (do not silently upgrade their standing)

- SCITT architecture: [RFC 9943](https://www.rfc-editor.org/rfc/rfc9943)
- Nicholas Templeman, [Measurement Capsule -00 §2 and §7.2](https://datatracker.ietf.org/doc/html/draft-templeman-scitt-measurement-capsule-00#section-7.2) — a **draft**. `effect_reference` composition is proposed and not demonstrated by its published implementation.
- Joel Hillier, [CAP-1 -00](https://datatracker.ietf.org/doc/html/draft-hillier-coverage-attestation-00) — a **draft** about bounded populations and absence assertions.
- Historical background: Joel's 8 October email explained the report's contribution categories and submission rules; the 12 October deposit did **not** admit our proposed fixture (Appendix A item 16). This repo does not claim otherwise.
- Prior source-level work: [CounterProof #188](https://github.com/hippoley/CounterProof/pull/188) and [#190](https://github.com/hippoley/CounterProof/pull/190); their status is independent of these illustrative tests.

## Run, inspect, falsify

```bash
python3 docs/scitt-evidence-boundary/verify.py docs/scitt-evidence-boundary/cases.json
python3 -m unittest discover -s docs/scitt-evidence-boundary -p 'test_*.py'
sha256sum docs/scitt-evidence-boundary/{README.md,cases.json,verify.py,test_verify.py}
git rev-parse HEAD
```

The checker outputs a machine-readable summary, exits nonzero on unexpected results, and never reports an affirmative physical-completion or SCITT-conformant result.

| Case | Input state | Expected consumer conclusion |
| --- | --- | --- |
| `ack_only` | Command accepted, ACK received | `UNCHECKABLE` for physical effect |
| `matching_bytes_no_observation` | Digest verified, no object observation | `UNCHECKABLE` |
| `motor_not_object` | Motor telemetry, no independent window-object sensor | `UNCHECKABLE` |
| `self_reported_separation` | Different declared domains, no external proof | `INDEPENDENCE_UNPROVEN` |
| `observed_mismatch` | Measurement contradicts declared position | `INCONSISTENT` |
| `observed_match` | Observation matches declared state | `CONSISTENT_LIMITED` (not completion proof) |
| `bad_reference_digest` | Different actual digest than declared | `REFERENCE_MISMATCH` |

**Deliberate non-goal:** these state names are **local test-harness labels**, *not* Measurement Capsule vocabulary or CAP-1 conformance results.

## Reviewable argument, step by step

1. **Define the claim under examination.** "Command accepted" and "physical window closed" are different claims. Falsifier: drop the ACK or keep ACK while preventing movement.
2. **Identify exact provenance.** Pin the implementation commit, observation bytes and registered signed-statement octets separately. Falsifier: change one octet and test digest mismatch.
3. **Bound the measured subject.** Motor-shaft position is not necessarily the window object's observed position. Falsifier: jam/disconnect actuator and compare sources.
4. **Classify origin and relationships.** A second key/process/control domain is a declaration, not proof of organizational independence. Falsifier: both sensors under one administrator.
5. **Separate cryptographic checks from measurement checks.** A SCITT receipt (if present) is about registration, not truth of physical effect. Falsifier: register a false or unrelated statement.
6. **Report uncheckable states.** Missing observation or reference must not yield a positive outcome.
7. **Separate evidence from decisions.** A downstream policy owner makes any operational action decision; this lab makes none.
8. **Expose the reproduction gap.** Another machine re-running these *synthetic* cases proves only software behavior, not independent hardware measurement.

## Admission gates for a future *real-hardware* packet

- [ ] Raw, non-synthetic timestamped **window-object** observation; instrument, units, method, calibration/limitations and safe anonymization reviewed.
- [ ] Exact accepted command identity, separate controller ACK and motor telemetry with source timestamps.
- [ ] Publicly retrievable, immutable reference to the signed execution statement; digest over **registered bytes** and profile/revision pinned.
- [ ] SCITT receipt bytes and verification transcript **if actually available**; explicitly say `absent` otherwise.
- [ ] Relationship and control/failure-domain evidence with `independence_proven=false` unless independently substantiated.
- [ ] Reproduce from a clean network/identity without private repository permissions; version-pinned downloads and `sha256sum`.
- [ ] External consumer executes verification and publishes its own findings and limitations.
- [ ] No claim of SCITT certification, independent observer, or physical completion without a separate justified standard of proof.

**Gate status today:** these real-hardware conditions are **not met by this fixture**. Request for independent implementation review is premature until a separate packet meets them.

## Long-horizon compatibility strategy (our proposal, not others' roadmaps)

| Horizon | Durable artifact | Breakage/review trigger |
| --- | --- | --- |
| 0–6 months | Small negative tests + eventual hardware packet | A reviewer cannot reproduce or disagrees with a case |
| 6–18 months | Versioned consumer adapters to two real implementations | New draft revision changes field meaning or octet framing |
| 18–36 months | Cross-implementation regression suite, adversarial test corpus | Another implementer reports incompatibility |
| 3–5 years | Governance for fixture review, deprecation and provenance | Tool becomes dependent on one vendor or sole maintainer |
| 5–10 years | Long-lived, reproducible semantics/claim-boundary test vectors | Protocol succession, cryptographic migration, new actuator classes |

This is a maintenance **hypothesis**, not a forecast of SCITT's standards roadmap. We will delete or revise cases that duplicate earlier stronger upstream work, including the previously acknowledged C5 population-pin finding.

## Evidence ledger

| Assertion | Evidence today | Confidence |
| --- | --- | --- |
| Public bounded-claim demonstration exists | This branch, fixtures, tests and checker | Executable local tests (only if actually run) |
| External party reproduced this fixture | No published third-party receipt | **NOT ESTABLISHED** |
| WindowPilot hardware observation verified | No public raw observation packet here | **NOT ESTABLISHED** |
| Signed execution statement + SCITT receipt validated here | No actual signed bytes included | **NOT ESTABLISHED** |
| Accepted into October SCITT interop report | Appendix A item 16 says proposed, not admitted | **NOT ADMITTED** |

## How to contribute with minimal reviewer burden

Open an issue identifying **one failing case**, the pinned version, a reproduction command, expected behavior, actual output, and evidence. Please do not ask an upstream author to investigate a vague integration proposal or private URL. This package makes **no request** for changes to either Internet-Draft.

## License and disclosure

This directory is newly authored example code and documentation. It intentionally does not redistribute CAP-1 code, Measurement Capsule implementation code, or private hardware data. Check repository-wide licensing before reuse; standards documents remain under their own terms.
