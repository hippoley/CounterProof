"""Zero-friction GitHub onboarding for Counterproof."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestRunnerDetection:
    command: str
    runner: str
    confidence: str
    evidence: tuple[str, ...]
    ecosystem: str = "generic"
    setup_commands: tuple[str, ...] = ()


def _read_json(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _node_setup_commands(repo_root: Path, *, playwright: bool = False) -> tuple[str, ...]:
    if (repo_root / "pnpm-lock.yaml").is_file():
        commands = ("corepack enable", "pnpm install --frozen-lockfile")
    elif (repo_root / "yarn.lock").is_file():
        commands = ("corepack enable", "yarn install --immutable")
    elif (repo_root / "package-lock.json").is_file():
        commands = ("npm ci",)
    else:
        commands = ("npm install",)
    if playwright:
        commands = (*commands, "npx playwright install --with-deps")
    return commands


def _python_setup_commands(repo_root: Path) -> tuple[str, ...]:
    commands: list[str] = ["python -m pip install --upgrade pip"]
    requirements = repo_root / "requirements.txt"
    pyproject = repo_root / "pyproject.toml"
    setup_py = repo_root / "setup.py"

    if requirements.is_file():
        commands.append("python -m pip install -r requirements.txt")
    if pyproject.is_file() or setup_py.is_file():
        commands.append("python -m pip install -e .")
    commands.append("python -m pip install pytest")
    return tuple(dict.fromkeys(commands))


def detect_test_runner(repo_root: Path) -> TestRunnerDetection:
    """Detect a practical changed-test command from common project files."""
    repo_root = repo_root.resolve()
    package_json = repo_root / "package.json"
    if package_json.is_file():
        package = _read_json(package_json)
        deps: dict[str, object] = {}
        for key in ("dependencies", "devDependencies"):
            value = package.get(key, {})
            if isinstance(value, dict):
                deps.update(value)

        if "@playwright/test" in deps:
            return TestRunnerDetection(
                command="npx playwright test {tests}",
                runner="playwright",
                confidence="high",
                evidence=("package.json:@playwright/test",),
                ecosystem="node",
                setup_commands=_node_setup_commands(repo_root, playwright=True),
            )
        if "vitest" in deps:
            return TestRunnerDetection(
                command="npx vitest run {tests}",
                runner="vitest",
                confidence="high",
                evidence=("package.json:vitest",),
                ecosystem="node",
                setup_commands=_node_setup_commands(repo_root),
            )
        if "jest" in deps:
            return TestRunnerDetection(
                command="npx jest {tests} --runInBand",
                runner="jest",
                confidence="high",
                evidence=("package.json:jest",),
                ecosystem="node",
                setup_commands=_node_setup_commands(repo_root),
            )

        scripts = package.get("scripts", {})
        if isinstance(scripts, dict) and isinstance(scripts.get("test"), str):
            return TestRunnerDetection(
                command="npm test -- {tests}",
                runner="npm-test",
                confidence="medium",
                evidence=("package.json:scripts.test",),
                ecosystem="node",
                setup_commands=_node_setup_commands(repo_root),
            )

    pyproject = repo_root / "pyproject.toml"
    pytest_ini = repo_root / "pytest.ini"
    tox_ini = repo_root / "tox.ini"
    if (
        pytest_ini.is_file()
        or tox_ini.is_file()
        or (pyproject.is_file() and "pytest" in pyproject.read_text(encoding="utf-8"))
        or (repo_root / "tests").is_dir()
    ):
        return TestRunnerDetection(
            command="python -m pytest -q {tests}",
            runner="pytest",
            confidence="high" if pytest_ini.is_file() or pyproject.is_file() else "medium",
            evidence=tuple(
                item
                for item, exists in (
                    ("pytest.ini", pytest_ini.is_file()),
                    ("tox.ini", tox_ini.is_file()),
                    ("pyproject.toml", pyproject.is_file()),
                    ("requirements.txt", (repo_root / "requirements.txt").is_file()),
                    ("tests/", (repo_root / "tests").is_dir()),
                )
                if exists
            ),
            ecosystem="python",
            setup_commands=_python_setup_commands(repo_root),
        )

    if (repo_root / "go.mod").is_file():
        return TestRunnerDetection(
            command="go test ./...",
            runner="go-test",
            confidence="high",
            evidence=("go.mod",),
            ecosystem="go",
        )

    if (repo_root / "Gemfile").is_file():
        gemfile = (repo_root / "Gemfile").read_text(encoding="utf-8")
        if "rspec" in gemfile.lower():
            return TestRunnerDetection(
                command="bundle exec rspec {tests}",
                runner="rspec",
                confidence="high",
                evidence=("Gemfile:rspec",),
                ecosystem="ruby",
            )

    if (repo_root / "pom.xml").is_file():
        return TestRunnerDetection(
            command="mvn test",
            runner="maven-test",
            confidence="medium",
            evidence=("pom.xml",),
            ecosystem="java",
        )

    if (repo_root / "gradlew").is_file():
        return TestRunnerDetection(
            command="./gradlew test",
            runner="gradle-test",
            confidence="medium",
            evidence=("gradlew",),
            ecosystem="java",
        )

    raise ValueError(
        "could not detect a supported test runner; pass --test-command explicitly"
    )


def _ecosystem_setup_yaml(detection: TestRunnerDetection | None) -> str:
    if detection is None:
        return """      # Install your project's dependencies before Counterproof.
      # Example: pip install -e .[dev] / npm ci / bundle install
"""

    chunks: list[str] = []
    if detection.ecosystem == "node":
        chunks.append(
            """      - uses: actions/setup-node@v4
        with:
          node-version: "22"
"""
        )
    elif detection.ecosystem == "go":
        chunks.append(
            """      - uses: actions/setup-go@v5
        with:
          go-version-file: go.mod
"""
        )
    elif detection.ecosystem == "ruby":
        chunks.append(
            """      - uses: ruby/setup-ruby@v1
        with:
          bundler-cache: true
"""
        )
    elif detection.ecosystem == "java":
        chunks.append(
            """      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: "21"
"""
        )

    if detection.setup_commands:
        commands = "\n".join(f"          {command}" for command in detection.setup_commands)
        chunks.append(
            "      - name: Install project dependencies\n"
            "        run: |\n"
            f"{commands}\n"
        )

    return "\n".join(chunks)


def render_github_workflow(
    *,
    test_command: str,
    detection: TestRunnerDetection | None = None,
    require_witness: bool = False,
    require_clean_integrity: bool = False,
) -> str:
    witness = "true" if require_witness else "false"
    integrity = "true" if require_clean_integrity else "false"
    escaped_command = test_command.replace('"', '\\"')
    head_expr = "$" + "{{ github.event.pull_request.head.sha }}"
    setup_yaml = _ecosystem_setup_yaml(detection)

    return f"""name: Counterproof

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  proof:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: {head_expr}
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

{setup_yaml}
      - uses: hippoley/SkillFactory@main
        with:
          test-command: "{escaped_command}"
          require-witness: "{witness}"
          require-clean-integrity: "{integrity}"
"""


def init_github(
    repo_root: Path,
    *,
    test_command: str | None = None,
    force: bool = False,
    require_witness: bool = False,
    require_clean_integrity: bool = False,
) -> tuple[Path, TestRunnerDetection | None]:
    """Create .github/workflows/counterproof.yml without overwriting by default."""
    repo_root = repo_root.resolve()
    detection: TestRunnerDetection | None = None
    if test_command is None:
        detection = detect_test_runner(repo_root)
        test_command = detection.command

    destination = repo_root / ".github" / "workflows" / "counterproof.yml"
    if destination.exists() and not force:
        raise FileExistsError(
            f"{destination} already exists; use --force to replace it"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_github_workflow(
            test_command=test_command,
            detection=detection,
            require_witness=require_witness,
            require_clean_integrity=require_clean_integrity,
        ),
        encoding="utf-8",
    )
    return destination, detection
