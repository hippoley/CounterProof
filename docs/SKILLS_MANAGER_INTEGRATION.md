# Skills Manager integration — experimental (2026-10-19)

## What has actually been integrated

1. The complete upstream Skills Manager repository is pinned as a Git submodule under vendor/skills-manager at commit 7f92c21882456f6b801884818dd898d19bc20ff9 (v1.42.2). Upstream includes the desktop UI, marketplace, presets, 54 agent integrations, project/global workspaces, Git backup and CLI.
2. CounterProof's new optional command group is counterproof skill. It provides inspect (static, no Skill execution), evolve (trace-derived proposed change), and manager (explicit delegation to the separately installed upstream CLI).
3. Existing counterproof check, witness, and the original skill-factory executable remain available. This change does not run or change those workflows.

## Try it locally

    git clone --recurse-submodules https://github.com/hippoley/CounterProof.git
    cd CounterProof
    git checkout feat/skills-manager-skill-mode-20261019
    git submodule update --init vendor/skills-manager
    python -m pip install -e .
    counterproof skill --help
    counterproof skill inspect skills/thing-model-condition-template --json-output

To use the Skills Manager CLI, install the upstream binary from its matching release, or build its CLI from the pinned submodule per upstream README. Then run:

    counterproof skill manager -- skills list
    counterproof skill manager -- skills status my-skill
    # Mutating deployments are intentionally blocked in the CounterProof manager bridge.
    # Use "counterproof skill promote" only after independent paired evaluation.

Use --binary /absolute/path/to/skills-manager-cli to select an executable. The manager commands have their own flags; dry-run is not universally supported. No agent deployment happens without an explicit upstream command.

To propose a Skill from a trace, use a real compatible input:

    counterproof skill evolve <TRACE.json> --out EVOLUTION_PACKET.json

An evolution packet is a hypothesis/proposal, not a validated new Skill or an authorization to deploy it.

## Installable CounterProof Skill (preview)

A native Agent Skill is now included at [skills/counterproof-pr-proof/SKILL.md](../skills/counterproof-pr-proof/SKILL.md). It teaches coding agents to request narrow local BASE/HEAD evidence and not overstate green CI. Its evals/ folder contains **proposed test fixtures**, not measured trigger accuracy.

Install/import using the separately installed upstream Skills Manager GUI or
native CLI (after reviewing the third-party Skill). The CounterProof bridge
does not perform installations:

    skills-manager-cli skills install https://github.com/hippoley/CounterProof/tree/feat/skills-manager-skill-mode-20261019/skills/counterproof-pr-proof
    counterproof skill manager -- skills status counterproof-pr-proof

The install command is an example, not verified against a real upstream binary.
For actual deployment, use the evidence-gated `counterproof skill evaluate`
followed by `counterproof skill promote`; direct deployment through our bridge
is intentionally blocked.

Confirm agent identifiers and CLI flags against the installed upstream version before live deployment. The commands above are integration examples, **not claims of successful execution**.
## Proof-gated A/B evaluation and deployment — experimental

The new **fail-closed** path is implemented in
[skill_factory/skill_gate.py](../skill_factory/skill_gate.py) and exposed by
`counterproof skill evaluate` and `counterproof skill promote`.

The unrestricted `counterproof skill manager -- ...` bridge has been
**restricted to read-only status/list/show calls**. It rejects install/sync/
deploy calls instead of creating an accidental bypass. The upstream desktop
app and upstream native CLI remain independently usable; this guard applies
only to the CounterProof bridge, not to third-party software.

### Create a local signing key (never commit it)

```bash
counterproof skill keygen ~/.counterproof-skill-gate.key
```

The 32-byte key is created without overwrite and with restricted file
permissions. Keep it OUTSIDE the managed Skill tree, Git repositories and
synchronized/backup folders. A local HMAC protects the receipt from
unintentional edits or replacement by a party without the secret; it is
**not** an independent third-party attestation and does not defend against
a malicious evaluator that can access the same user's key.

### Prepare an external holdout suite and real runner

Example `holdout.json` (store OUTSIDE the managed Skill tree):

```json
{
  "schema_version": "counterproof.skill-suite/v0.1",
  "suite_id": "reviewer-owned-2026-10",
  "cases": [
    {"id": "s1", "prompt": "Case one prompt", "expected_output": "expected one"},
    {"id": "s2", "prompt": "Case two prompt", "expected_output": "expected two"},
    {"id": "s3", "prompt": "Case three prompt", "expected_output": "expected three"},
    {"id": "s4", "prompt": "Case four prompt", "expected_output": "expected four"}
  ]
}
```

Runner contract: an independently selected **executable** reads one JSON
request from stdin and emits `{"output":"..."}` on stdout, exit status 0.
Request fields are
`schema_version = counterproof.skill-runner/v0.1`,
`case_id`, `prompt`, `arm` (baseline/skill), and `skill_path` (null
for baseline). A nonzero exit or invalid JSON blocks evaluation. This
minimal exact-match oracle is intentionally strict and not suitable for
open-ended natural-language scoring without an externally fixed grader.

No hidden cases or real model implementation are bundled with this preview.
The provided repository tests use a SIMULATED manager and runner to exercise
gate logic, not to prove actual agent improvement.

### Run actual paired evaluation

```bash
counterproof skill evaluate my-skill \
  --suite /external/holdout.json \
  --runner-binary /absolute/path/to/trusted-evaluation-runner \
  --manager-binary /absolute/path/to/skills-manager-cli \
  --key ~/.counterproof-skill-gate.key \
  --min-gain 1 \
  --out /external/SKILL_GATE_RECEIPT.json
```

The gate requires at least four unique externally located cases, one
measured gain, zero per-case regressions, a stable manager/runner binary,
unchanged external suite and the same managed Skill source tree throughout
the evaluation. The result is only a **scoped paired observation**; path
separation does not independently establish data author independence,
oracle validity or generalization.

### Preflight and explicitly apply to multiple agents

```bash
# Does not write agent skill directories:
counterproof skill promote my-skill \
  --receipt /external/SKILL_GATE_RECEIPT.json \
  --suite /external/holdout.json \
  --key ~/.counterproof-skill-gate.key \
  --agent codex --agent claude_code

# After reviewing the dry-run output, explicitly authorize live deployment:
counterproof skill promote my-skill \
  --receipt /external/SKILL_GATE_RECEIPT.json \
  --suite /external/holdout.json \
  --key ~/.counterproof-skill-gate.key \
  --agent codex --agent claude_code \
  --apply --confirm-sha256 <EXACT_EVALUATED_SKILL_TREE_SHA256>
```

Promotion checks the local HMAC, honest case-count/verdict arithmetic,
unchanged suite/runner/manager/Skill fingerprints, exact user-named
agents and upstream CLI dry-run. Only with `--apply` does it request
deployment. It then checks upstream status and hashes each target Skill
tree; a missing/mismatched target is a **partial deployment failure**,
not a successful result. This version does **not** implement atomic
cross-agent rollback. If a partial deployment occurs, inspect and
recover it manually; do not claim all-or-nothing transactional semantics.

The receipt is an **evidence gate for file deployment**, not a portable
certification of model behavior on every target Agent.

### Offline regression checks

```bash
python -m pytest -q tests/unit/test_skill_gate.py tests/unit/test_skills_mode.py
```

The suite contains simulated-manager tests for forged self-hashes, a
different signing key, source/suite/runner/manager drift, missing gains,
case regression, duplicate agent names, strict preflight, and partial
target deployment. **Written tests are not passing test evidence until
the above exact command is executed and its result recorded.**


## Honest feature boundaries

| Capability | Preview branch status |
|---|---|
| Entire upstream source | PINNED via submodule, not copied |
| Upstream desktop GUI | AVAILABLE in submodule; build/run separately |
| Marketplace, presets, synchronization | UPSTREAM software only; access via its installed CLI or GUI |
| CLI command forwarding | IMPLEMENTED locally in Python |
| Static SKILL.md inspection | IMPLEMENTED; heuristic; no execution |
| Skill candidate proposals | WRAPPED around existing trace pipeline |
| Skill behavioral improvement proof | PAIRED EVALUATION GATE IMPLEMENTED; REAL MODEL PROOF NOT YET RUN |
| Shared Rust/Python state/database | NOT IMPLEMENTED |
| Embedded desktop window | NOT IMPLEMENTED |
| Cross-platform full E2E verification | NOT YET RUN |

## Security, provenance, truthfulness

- Heuristic static PASS is not a security audit or a behavioral witness.
- The CLI bridge uses a subprocess argument vector, never the shell; launching the upstream binary is explicit.
- Generated candidates are not deployed automatically.
- The Python package does not download or run the desktop program on installation.
- Third-party Skills may contain arbitrary code/instructions. Treat them as untrusted and inspect before enabling.
- Upstream project and credit: https://github.com/xingkongliang/skills-manager — MIT License, Copyright (c) 2026 Tianliang Zhang. Upstream LICENSE is kept in the submodule. CounterProof remains Apache-2.0 for original code.
- This integration is not upstream-endorsed. Keep the original full source and copyright intact.

## Local first: minimize Actions cost

    python -m pytest -q tests/unit/test_skills_mode.py

Only trigger targeted CI after local validation when there is a real code change requiring remote proof. The feature branch does not match current CI push branch filters (main/develop). Do not merge to main or open a PR simply to run CI.

## Next verification gates

1. Test against the real pinned skills-manager-cli and measure exact CLI protocol/version compatibility.
2. Check Windows/macOS/Linux CLI and desktop installation flows separately.
3. Verify a before/after Skill behavior change against independent evaluation data and CounterProof receipts.
4. Add packaging/migration tests for existing SkillFactory registry alongside upstream library.
5. Invite third-party reproducible compatibility issues; never advertise verified cross-agent deployment before receiving the evidence.
