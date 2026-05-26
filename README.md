# Skill Factory

> **Forge skills from real failures, not imagination.**

Skill Factory is an open-source framework for creating, evaluating, and managing **Agent Skills** — reusable, versioned capability packages that make AI agents smarter over time.

Instead of writing skills from scratch, Skill Factory extracts them from real task trajectories, failure logs, human corrections, and execution feedback — then validates every skill with deterministic verifiers and A/B evals before it enters the registry.

---

## The Problem

Most teams hit the same wall:

- Prompt templates cannot cover open-ended scenarios
- Hand-crafting rules does not scale
- LLMs hallucinate skills with no grounding in real domain knowledge
- There is no way to know if a skill actually helps

## The Solution

    Real tasks / Failures / Human corrections / Execution logs
            |
    LLM synthesizes Skill candidates
            |
    Static checks + Trigger tests + A/B task evaluation
            |
    Deterministic verifier / LLM judge / Human review
            |
    Versioned Skill Registry

Skills are **forged from evidence**, not invented. Every skill must prove it improves task outcomes before it enters the registry.

---

## Core Concepts

| Concept | Description |
|---|---|
| **Skill** | A directory with SKILL.md + scripts + references + assets + evals |
| **Skill Registry** | Versioned store of validated skills, indexed by domain and trigger |
| **Skill Generator** | Synthesizes skill candidates from trajectories and feedback |
| **Skill Evaluator** | Runs A/B tests: with skill vs without skill |
| **Skill Verifier** | Deterministic checks: schema, syntax, safety, conflicts |
| **Progressive Disclosure** | Load only name+description at startup; full skill on match |

---

## Quick Start

    pip install skill-factory

    skill-factory generate --trajectory trajectory.json --output skills/
    skill-factory validate skills/my-skill/
    skill-factory eval skills/my-skill/ --task-set evals/tasks.json
    skill-factory registry list
    skill-factory registry add skills/my-skill/

---

## Project Structure

    skill_factory/
      registry/       # Skill Registry: store, index, version
      generator/      # Skill Generator: trajectory to skill candidate
      evaluator/      # Skill Evaluator: A/B eval runner
      verifier/       # Skill Verifier: deterministic checks
      cli/            # CLI entry points
    skills/           # Example skills
    tests/            # Unit and integration tests
    docs/             # Documentation

---

## Roadmap

- [x] Skill directory format (SKILL.md spec)
- [x] Skill Registry (add, list, get, remove)
- [x] Static verifier (frontmatter, schema, safety)
- [x] Trigger evaluator (should/should-not trigger)
- [x] A/B eval runner
- [ ] Trajectory-based skill generator (LLM)
- [ ] LLM judge integration
- [ ] Red team / safety scanner
- [ ] Web UI for skill review
- [ ] GitHub Actions CI for skill validation

---

## License

Apache 2.0
