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

| Human review claim / failure mode | Exact test | BASE | HEAD | Submitted-test evidence | Oracle alignment | Overall claim |
|---|---|---:|---:|---|---|---|
| Work-pool default volumes must reach the Docker container when adhoc bundle storage is not separately configured | `test_submit_adhoc_run_uses_work_pool_default_volumes` | **FAIL** | **PASS** | **WITNESSED** | **UNVERIFIED** | **WITNESSED (submitted judge)** |
| Customized `job_configuration.volumes` must keep its configured volume **and** the internal `/tmp` bundle mount | `test_submit_adhoc_run_preserves_configured_volumes` | **FAIL** | **PASS** | **WITNESSED** | **UNVERIFIED** | **WITNESSED (submitted judge)** |
| Full Docker-daemon / end-to-end runtime behavior | Not exercised by these focused tests | — | — | **UNPROVEN** | **UNVERIFIED** | **UNPROVEN** |

## Assertion / failure excerpts

### 1. Default volume propagation

BASE reaches normal pytest execution and fails:

```text
test_submit_adhoc_run_uses_work_pool_default_volumes

assert 'result-storage:/result-storage' in ['/tmp/...:/tmp/']
```

HEAD passes the same test.

### 2. Customized job-configuration volumes + internal bundle mount

BASE reaches normal pytest execution and fails:

```text
test_submit_adhoc_run_preserves_configured_volumes

assert any(volume.endswith(':/tmp/') for volume in call_volumes)
```

The custom `custom:/custom` volume is present, but the internal temporary `/tmp` bundle mount required by the review is absent.

HEAD passes the same test with both properties preserved.

## Reviewer-facing conclusion

```text
default work-pool volume propagation
  submitted-test evidence  WITNESSED
  oracle alignment         UNVERIFIED
  overall                  WITNESSED (submitted judge)

custom template volume + internal /tmp
  submitted-test evidence  WITNESSED
  oracle alignment         UNVERIFIED
  overall                  WITNESSED (submitted judge)

live Docker runtime
  submitted-test evidence  UNPROVEN
  oracle alignment         UNVERIFIED
  overall                  UNPROVEN
```

This does not replace re-review of the implementation. It proves only that the submitted judge now distinguishes BASE from HEAD for both concrete review concerns.
