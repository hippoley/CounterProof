<div align="center">

# 🏭 Skill Factory

**Forge agent skills from real task failures, not imagination.**

[![CI](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml/badge.svg)](https://github.com/hippoley/SkillFactory/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## 🧬 EvoPR — Pull Requests for Agent Behavior

> **Your agent can rewrite itself. Make it open a pull request first.**

SkillFactory is growing beyond trajectory → SKILL.md distillation. **EvoPR** turns a real failure
into competing causal hypotheses, proposes the smallest behavior mutation across Skill / Policy /
Router / Memory / Tool, replays the change, and emits a reviewable **Behavior PR** with a rollback
reference.

~~~text
failure
  ↓
Decision Capsule + Outcome Receipt
  ↓
causal hypotheses
  ↓
minimal behavior mutations
  ↓
counterfactual replay + holdout
  ↓
Behavior Diff
  ↓
EVOLUTION PR
  ↓
shadow / canary
  ↓
merge or rollback
~~~

Try the first prototype:

~~~bash
pip install -e .
evopr build examples/evolution_pr.json --out EVOLUTION_PR.md
~~~

See [docs/EVOPR.md](docs/EVOPR.md) for the Verified Agent Evolution architecture.

---

Skill Factory is an open-source framework for **creating, evaluating, and managing Agent Skills** — reusable, versioned capability packages that make AI agents smarter over time.

Instead of writing skills from scratch, Skill Factory **extracts them from real task trajectories**, failure logs, human corrections, and execution feedback — then validates every skill with deterministic verifiers and A/B evals before it enters the registry.

> A skill only enters the registry if it proves it improves task outcomes. No evidence, no entry.

---

## The Problem

Most teams hit the same wall:

| Problem | Why it hurts |
|---|---|
| Prompt templates can't cover open-ended scenarios | Every new edge case needs manual work |
| Hand-crafting rules doesn't scale | 100 templates → 1000 edge cases |
| LLMs hallucinate skills with no domain grounding | Garbage in, garbage out |
| No way to know if a skill actually helps | Skills accumulate, quality degrades |

## The Solution: Skill Factory Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│  Real tasks · Failures · Human corrections · Exec logs      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   LLM Skill Generator  │  trajectory → SKILL.md candidate
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Static Verifier      │  frontmatter · safety · schema
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   A/B Eval Runner      │  with skill vs without skill
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  Deterministic Verifier│  JSON schema · state machine · safety
              │  + LLM Judge           │  pass rate · token delta · latency
              │  + Human Review        │  low-confidence & high-risk only
              └────────────┬───────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Versioned Registry   │  indexed · searchable · auditable
              └────────────────────────┘
```

---

## Architecture

```
skill_factory/
├── models.py          # SkillMeta · Skill · EvalCase · EvalReport
├── loader.py          # SKILL.md parser · progressive disclosure
├── registry/          # Versioned skill store (add · get · remove · search)
├── verifier/          # Static checker (frontmatter · safety · schema · evals)
├── evaluator/         # A/B eval runner (with skill vs without skill)
├── generator/         # Trajectory model · LLM prompt builder
└── cli/               # CLI: validate · generate · registry · eval

skills/                # Example skills (one directory per skill)
├── thing-model-condition-template/
├── energy-saving-schedule/
├── multi-sensor-priority-control/
└── device-safety-interlock/

tests/
├── unit/              # 15+ unit tests
└── integration/

docs/
├── skill-format.md    # SKILL.md specification
└── eval-guide.md      # Evaluation guide
```

---

## Quick Start

PyPI release is still on the roadmap. Install the current code from source so the commands below match the repository you are reading.

```bash
git clone https://github.com/hippoley/SkillFactory.git
cd SkillFactory
pip install -e .

# Generate a skill from a real task trajectory
# Add .[llm] when using OpenAI or Anthropic providers.
pip install -e ".[llm]"
skill-factory generate trajectory.json --provider openai --output skills/

# Validate a skill (static checks)
skill-factory validate skills/my-skill/

# Run A/B eval
skill-factory eval skills/my-skill/ --task-set evals/tasks.json

# Manage the registry
skill-factory registry list
skill-factory registry add skills/my-skill/
skill-factory registry search "smart-home"
skill-factory registry remove my-skill

# Optional review UI
pip install -e ".[web]"
skill-factory serve
```

---

## Skill Directory Format

Every skill is a self-contained directory:

```
my-skill/
├── SKILL.md                    # Required: frontmatter + instructions
├── scripts/
│   └── validate.py             # Deterministic verifier script
├── references/
│   └── protocol.md             # Domain knowledge docs
├── assets/
│   ├── output.schema.json      # Expected output JSON schema
│   └── examples.json           # Worked examples
└── evals/
    ├── evals.json              # A/B eval test cases
    └── trigger_queries.json    # Should / should-not trigger queries
```

**SKILL.md** uses YAML frontmatter + Markdown:

```yaml
---
name: my-skill
description: Use this skill when... (one sentence, specific trigger)
version: "0.1.0"
license: apache-2.0
compatibility: Requires schema v3
metadata:
  owner: team-name
  domain: smart-home
  tags: [iot, condition, behavior-tree]
---

## Purpose
## When to use
## Procedure
## Gotchas
## Validation
```

---

## Core Concepts

| Concept | Description |
|---|---|
| **Skill** | A directory with `SKILL.md` + scripts + references + assets + evals |
| **Skill Registry** | Versioned store of validated skills, indexed by domain and trigger |
| **Skill Generator** | Synthesizes skill candidates from trajectories and LLM feedback |
| **Skill Evaluator** | Runs A/B tests: with skill vs without skill, measures delta |
| **Skill Verifier** | Deterministic checks: schema, syntax, safety, conflict detection |
| **Progressive Disclosure** | Load only `name`+`description` at startup; full skill on match |

---

## Evaluation Philosophy

Skills are evaluated on measurable signals — not intuition:

| Metric | Description |
|---|---|
| **Pass rate delta** | Primary: did the skill improve task success rate? |
| **Schema compliance** | Does output pass deterministic validators? |
| **Trigger precision** | Low false-positive and false-negative rates |
| **Token delta** | Did the skill increase token cost significantly? |
| **Safety** | No prompt injection, no unauthorized actions |

A skill passes if: `pass_rate_delta > 0` AND no safety violations AND `token_delta < 20%`.

---

## Roadmap

- [x] Skill directory format (SKILL.md spec)
- [x] Skill Registry (add, list, get, remove, search)
- [x] Static verifier (frontmatter, schema, safety patterns)
- [x] Trigger evaluator (should / should-not trigger)
- [x] A/B eval runner
- [x] Example skill: `thing-model-condition-template`
- [x] `skill-factory generate` — LLM-powered skill synthesis from trajectories
- [ ] LLM judge integration (OpenAI / Anthropic)
- [ ] Red team / safety scanner (promptfoo integration)
- [x] Web UI for skill review (FastAPI review surface)
- [ ] More example skills (energy, multi-sensor, safety interlock)
- [ ] PyPI release

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). All skills submitted to the registry must pass the full eval pipeline.

---

## License

[Apache 2.0](LICENSE) — © 2025 Skill Factory Contributors
