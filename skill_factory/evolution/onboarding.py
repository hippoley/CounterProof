"""Generate a conservative Counterproof GitHub workflow from repository signals."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunnerGuess:
    ecosystem: str
    test_command: str
    confidence: str
    reason: str
    setup_kind: str


def detect_runner(repo_root: Path) -> RunnerGuess:
    """Infer a practical test runner without pretending low-confidence guesses are safe."""
    repo_root = repo_root.resolve()

    package_json = repo_root / "package.json"
    if package_json.is_file():
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            package = {}
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        test_script = str(scripts.get("test", "")).lower()
        if "vitest" in test_script:
            return RunnerGuess(
                "node",
                "npx vitest run {tests}",
                "high",
                "package.json test script references Vitest",
                "node",
            )
        if "jest" in test_script:
            return RunnerGuess(
                "node",
                "npx jest {tests} --runInBand",
                "high",
                "package.json test script references Jest",
                "node",
            )
        if "playwright" in test_script:
            return RunnerGuess(
                "node",
                "npx playwright test {tests}",
                "high",
                "package.json test script references Playwright",
                "node",
            )
        if test_script:
            return RunnerGuess(
                "node",
                "npm test",
                "medium",
                "package.json provides a test script",
                "node",
            )
        return RunnerGuess(
            "node",
            "npm test",
            "low",
            "package.json detected but no test script was found",
            "node",
        )

    if (repo_root / "go.mod").is_file():
        return RunnerGuess(
            "go",
            "go test ./...",
            "high",
            "go.mod detected",
            "go",
        )

    if (repo_root / "Gemfile").is_file():
        return RunnerGuess(
            "ruby",
            "bundle exec rspec {tests}",
            "medium",
            "Gemfile detected",
            "ruby",
        )

    python_markers = (
        repo_root / "pyproject.toml",
        repo_root / "pytest.ini",
        repo_root / "setup.cfg",
        repo_root / "requirements.txt",
    )
    if any(path.is_file() for path in python_markers) or (repo_root / "tests").is_dir():
        setup_kind = (
            "python-requirements"
            if (repo_root / "requirements.txt").is_file()
            else "python-package"
        )
        return RunnerGuess(
            "python",
            "python -m pytest -q {tests}",
            "high" if (repo_root / "pytest.ini").is_file() else "medium",
            "Python project/test markers detected",
            setup_kind,
        )

    return RunnerGuess(
        "generic",
        "",
        "low",
        "No supported test-runner marker was detected",
        "generic",
    )


def _setup_yaml(kind: str) -> list[str]:
    if kind == "node":
        return [
            "      - uses: actions/setup-node@v4",
            "        with:",
            "          node-version: '22'",
            "      - run: npm ci",
        ]
    if kind == "go":
        return [
            "      - uses: actions/setup-go@v5",
            "        with:",
            "          go-version-file: go.mod",
        ]
    if kind == "ruby":
        return [
            "      - uses: ruby/setup-ruby@v1",
            "        with:",
            "          bundler-cache: true",
        ]
    if kind == "python-requirements":
        return [
            "      - uses: actions/setup-python@v5",
            "        with:",
            "          python-version: '3.11'",
            "      - run: python -m pip install -r requirements.txt",
            "      - run: python -m pip install pytest",
        ]
    if kind == "python-package":
        return [
            "      - uses: actions/setup-python@v5",
            "        with:",
            "          python-version: '3.11'",
            "      - run: python -m pip install -e .",
            "      - run: python -m pip install pytest",
        ]
    return []


def render_workflow(
    guess: RunnerGuess,
    *,
    action_ref: str = "main",
    require_witness: bool = False,
    require_clean_integrity: bool = False,
) -> str:
    """Render a copy-pasteable workflow that checks out the actual PR head."""
    pr_head_expr = "$" + "{{ github.event.pull_request.head.sha }}"
    lines = [
        "name: Counterproof",
        "",
        "on:",
        "  pull_request:",
        "",
        "permissions:",
        "  contents: read",
        "  pull-requests: write",
        "",
        "jobs:",
        "  regression-witness:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "        with:",
        f"          ref: {pr_head_expr}",
        "          fetch-depth: 0",
    ]
    lines.extend(_setup_yaml(guess.setup_kind))
    lines.extend(
        [
            f"      - uses: hippoley/SkillFactory/actions/witness@{action_ref}",
            "        with:",
            f"          test-command: {json.dumps(guess.test_command)}",
            f"          require-witness: {json.dumps(str(require_witness).lower())}",
            (
                "          require-clean-integrity: "
                + json.dumps(str(require_clean_integrity).lower())
            ),
            "",
        ]
    )
    return "\n".join(lines)


def initialize_github(
    repo_root: Path,
    *,
    test_command: str | None = None,
    action_ref: str = "main",
    require_witness: bool = False,
    require_clean_integrity: bool = False,
    force: bool = False,
) -> tuple[Path, RunnerGuess]:
    """Write .github/workflows/counterproof.yml without silently overwriting user config."""
    repo_root = repo_root.resolve()
    guess = detect_runner(repo_root)

    if test_command:
        guess = RunnerGuess(
            ecosystem=guess.ecosystem,
            test_command=test_command,
            confidence="explicit",
            reason="test command supplied explicitly",
            setup_kind=guess.setup_kind,
        )

    if not guess.test_command:
        raise ValueError(
            "Could not infer a test command safely. Re-run with --test-command."
        )

    target = repo_root / ".github" / "workflows" / "counterproof.yml"
    if target.exists() and not force:
        raise FileExistsError(
            f"{target} already exists; use --force to replace it"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_workflow(
            guess,
            action_ref=action_ref,
            require_witness=require_witness,
            require_clean_integrity=require_clean_integrity,
        ),
        encoding="utf-8",
    )
    return target, guess
