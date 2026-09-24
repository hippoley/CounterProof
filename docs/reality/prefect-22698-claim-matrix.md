# Claim / Evidence Matrix — PrefectHQ/prefect #22698

Source PR: https://github.com/PrefectHQ/prefect/pull/22698

Human review source:
https://github.com/PrefectHQ/prefect/pull/22698#pullrequestreview-4846013783

This matrix asks one narrow question: did the current head add behavioral evidence for the exact concerns raised in the human CHANGES_REQUESTED review?

## Execution provenance

- HEAD: `7604947bcaaec12a83505f842fbc6adb1b88275e`
- BASE: `ef4286181588e579f72854d9344f4a2f6d66a090`
- changed test file: `src/integrations/prefect-docker/tests/test_worker.py`
- CounterProof replay: https://github.com/hippoley/CounterProof/actions/runs/35979249605
- result protocol: `json-v1`
- evidence mode: `precise`
- evidence digest: `sha256:4d16ed79a10dacbfe15f025c39dbf9c4f0d7eb724eaa7c4647182ed305b9434f`

## Claim / evidence matrix

| Human review claim / failure mode | Exact test | BASE | HEAD | Oracle independently checked? | Status |
|---|---|---:|---:|---|---|
| Work-pool default volumes must reach the Docker container when adhoc bundle storage is not separately configured | `test_submit_adhoc_run_uses_work_pool_default_volumes` | **FAIL** | **PASS** | pytest + mocked Docker create-call contract | **WITNESSED** |
| Customized `job_configuration.volumes` must keep its configured volume **and** the internal `/tmp` bundle mount | `test_submit_adhoc_run_preserves_configured_volumes` | **FAIL** | **PASS** | pytest + mocked Docker create-call contract | **WITNESSED** |
| Full Docker-daemon / end-to-end runtime behavior | Not exercised by these focused tests | — | — | No live Docker daemon in this receipt | **UNPROVEN** |

## Assertion / failure excerpts

### 1. Default volume propagation

BASE reaches normal pytest execution and fails:

```text
test_submit_adhoc_run_uses_work_pool_default_volumes

assert 'result-storage:/result-storage' in ['/tmp/...:/tmp/']
```

The old implementation mounts only the temporary bundle volume and drops the work-pool default.

HEAD passes the same test.

### 2. Customized job-configuration volumes + internal bundle mount

BASE reaches normal pytest execution and fails:

```text
test_submit_adhoc_run_preserves_configured_volumes

assert any(volume.endswith(':/tmp/') for volume in call_volumes)
```

The custom `custom:/custom` volume is present, but the internal temporary `/tmp` bundle mount required by the reviewer is absent.

HEAD passes the same test with both properties preserved.

## Reviewer-facing conclusion

```text
default work-pool volume propagation       WITNESSED
custom template volume + internal /tmp     WITNESSED
live Docker runtime                        UNPROVEN
```

This does not replace re-review of the implementation.

It answers a narrower question: the current head now contains red-before / green-after behavioral coverage for both concrete failure modes requested in the human review.
