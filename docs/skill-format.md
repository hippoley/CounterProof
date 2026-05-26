# SKILL.md Format Specification

## Overview

A skill is a directory containing at minimum a `SKILL.md` file.
The file must have YAML frontmatter followed by Markdown content.

## Frontmatter

```yaml
---
name: my-skill                    # required: kebab-case identifier
description: One sentence...      # required: specific trigger condition
version: "0.1.0"                  # recommended: semantic version
license: apache-2.0               # recommended
compatibility: Requires X >= 1.0  # optional
metadata:
  owner: team-name                # optional
  domain: your-domain             # optional: used for indexing
  tags: [tag1, tag2]              # optional: used for search
---
```

## Required Frontmatter Fields

| Field | Type | Description |
|---|---|---|
| `name` | string | Unique kebab-case identifier |
| `description` | string | One sentence: when to use this skill |

## Recommended Body Sections

| Section | Purpose |
|---|---|
| `## Purpose` | What this skill does |
| `## When to use` | Trigger conditions (and when NOT to use) |
| `## Procedure` | Step-by-step instructions |
| `## Gotchas` | Common mistakes to avoid |
| `## Validation` | How to verify the output |
| `## References` | Links to supporting files |

## Directory Structure

```
my-skill/
  SKILL.md              # required
  scripts/              # optional: validator scripts
    validate.py
  references/           # optional: domain knowledge docs
    protocol.md
  assets/               # optional: schemas, examples
    output.schema.json
    examples.json
  evals/                # recommended: A/B eval test cases
    evals.json
    trigger_queries.json
```

## Description Quality Guidelines

- Be specific about the trigger: "Use this skill when X" not "Use this skill for Y"
- 20-300 characters
- Mention the domain or device type if relevant
- Avoid vague terms like "general", "various", "multiple"
