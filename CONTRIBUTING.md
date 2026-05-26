# Contributing to Skill Factory

## Submitting a Skill

1. Create a skill directory under `skills/` following the standard structure.
2. Run `skill-factory validate skills/your-skill/` -- must pass with no errors.
3. Run `skill-factory eval skills/your-skill/` -- must show positive delta vs baseline.
4. Open a PR. CI will re-run validation and eval automatically.

## Code Contributions

- Fork the repo and create a feature branch.
- Run `pip install -e ".[dev]"` to install dev dependencies.
- Run `pytest` before submitting.
- Follow the existing code style (ruff enforced).

## Reporting Issues

Open a GitHub Issue with:
- The skill or command that failed
- The full error output
- Your Python version and OS
