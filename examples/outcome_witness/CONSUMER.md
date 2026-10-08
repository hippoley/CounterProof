# Reproduce Outcome Witness without installing CounterProof

This is an **experimental fixture-only** consumer. It deliberately refuses inputs claiming to be live attestation. It is not a trusted verifier or hardware proof.

```sh
python examples/outcome_witness/consumer.py examples/outcome_witness/v0_1_vectors.json --output /tmp/outcome-results.json
cat /tmp/outcome-results.json
```

Expected results in order: `CONTRADICTED`, `VERIFIED`, `INCONCLUSIVE`, `INCONCLUSIVE`, `INCONCLUSIVE`. `VERIFIED` is only a verdict within the illustrative fixture trust profile.

An unrelated consumer can reproduce the results with Python stdlib and the two source files `consumer.py` and `check_vectors.py`; it need not install CounterProof. To graduate to real observations, source authentication, action/observation binding, and replay defenses are required. See [interop boundaries](../../docs/OUTCOME_WITNESS_INTEROP.md).
