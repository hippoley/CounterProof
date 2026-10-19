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
    counterproof skill manager -- skills deploy my-skill --agent codex --dry-run

Use --binary /absolute/path/to/skills-manager-cli to select an executable. The manager commands have their own flags; dry-run is not universally supported. No agent deployment happens without an explicit upstream command.

To propose a Skill from a trace, use a real compatible input:

    counterproof skill evolve <TRACE.json> --out EVOLUTION_PACKET.json

An evolution packet is a hypothesis/proposal, not a validated new Skill or an authorization to deploy it.

## Installable CounterProof Skill (preview)

A native Agent Skill is now included at [skills/counterproof-pr-proof/SKILL.md](../skills/counterproof-pr-proof/SKILL.md). It teaches coding agents to request narrow local BASE/HEAD evidence and not overstate green CI. Its evals/ folder contains **proposed test fixtures**, not measured trigger accuracy.

With the pinned Skills Manager CLI, import the skill from the preview branch, then explicitly deploy to the desired agent:

    counterproof skill manager -- skills install https://github.com/hippoley/CounterProof/tree/feat/skills-manager-skill-mode-20261019/skills/counterproof-pr-proof
    counterproof skill manager -- skills status counterproof-pr-proof
    counterproof skill manager -- skills deploy counterproof-pr-proof --agent codex --dry-run

Confirm agent identifiers and CLI flags against the installed upstream version before live deployment. The commands above are integration examples, **not claims of successful execution**.
## Honest feature boundaries

| Capability | Preview branch status |
|---|---|
| Entire upstream source | PINNED via submodule, not copied |
| Upstream desktop GUI | AVAILABLE in submodule; build/run separately |
| Marketplace, presets, synchronization | UPSTREAM software only; access via its installed CLI or GUI |
| CLI command forwarding | IMPLEMENTED locally in Python |
| Static SKILL.md inspection | IMPLEMENTED; heuristic; no execution |
| Skill candidate proposals | WRAPPED around existing trace pipeline |
| Skill behavioral improvement proof | NOT YET integrated end-to-end |
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
