# Skill Evaluation Guide

## Philosophy

A skill only enters the registry if it shows **measurable improvement** over baseline.
Feelings and intuition are not enough. Run the numbers.

## A/B Eval Structure

Every eval case runs twice:
- **Baseline**: task executed without the skill
- **With skill**: task executed with the skill injected into context

## evals.json Format

```json
{
  "skill": "my-skill",
  "version": "0.1.0",
  "cases": [
    {
      "id": "eval-001",
      "task": "Describe the task in natural language",
      "expected_pass": true,
      "verifier": "schema",
      "metadata": {"domain": "...", "complexity": "basic"}
    }
  ]
}
```

## Verifier Types

| Type | Description |
|---|---|
| `schema` | JSON Schema validation (deterministic) |
| `script` | Custom Python validator script |
| `llm` | LLM judge (use sparingly) |
| `human` | Manual review required |

## Metrics

| Metric | Description |
|---|---|
| Pass rate delta | Primary signal: did the skill improve success rate? |
| Token delta | Did the skill increase token usage significantly? |
| Latency delta | Did the skill add unacceptable latency? |
| Trigger precision | False positive and false negative rates |

## Acceptance Criteria

A skill passes eval if:
- Pass rate delta > 0 (any improvement)
- No safety violations introduced
- Token delta < 20% increase
- No regression on previously passing cases
