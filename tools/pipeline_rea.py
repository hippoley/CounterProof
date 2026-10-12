#!/usr/bin/env python3
"""Read-only, standard-library CI/CD surface inspector (experimental)."""
import argparse
import json
import re
from pathlib import Path

ASSIGN = re.compile(r"(?im)^\\s*(?:export\\s+)?([A-Z_]*(?:PASSWORD|TOKEN|API_KEY|SECRET_KEY))\\s*[:=]\\s*[\"']?([A-Za-z0-9_/+.-]{12,})[\"']?\\s*$")

def analyze(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    name = path.name
    platform = ("jenkins" if name == "Jenkinsfile" or name.endswith(".jenkinsfile")
                else "gitlab" if name == ".gitlab-ci.yml"
                else "github-actions" if ".github/workflows/" in path.as_posix()
                else "unknown")
    if platform == "unknown":
        raise ValueError("Expected Jenkinsfile, .gitlab-ci.yml or .github/workflows/*.yml")
    if platform == "jenkins":
        stages = re.findall(r"\\bstage\\s*\\(\\s*[\"']([^\"']+)[\"']", text)
        refs = re.findall(r"credentialsId\\s*:\\s*[\"']([^\"']+)[\"']", text)
    elif platform == "gitlab":
        stages = re.findall(r"^\\s{0,4}-\\s*([\\w-]+)\\s*$", text, re.M) if re.search(r"^stages:\\s*$", text, re.M) else []
        refs = re.findall(r"\\$\\{?([A-Z_][A-Z0-9_]*(?:TOKEN|KEY|PASSWORD|SECRET))\\}?", text)
    else:
        stages = re.findall(r"^\\s{2}([\\w-]+):\\s*$", text, re.M)
        refs = re.findall(r"\\$\\{\\{\\s*secrets\\.([A-Za-z_][\\w-]*)\\s*\\}\\}", text)
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        match = ASSIGN.search(line)
        if match and not re.search(r"\\$|\\{\\{|vault|credentials\\(", match.group(2), re.I):
            findings.append({"line": number, "rule": "possible-inline-secret",
                             "key": match.group(1), "severity": "high"})
    return {"schema": "pipeline-rea.report.v0", "platform": platform,
            "file": str(path), "stages_or_jobs": list(dict.fromkeys(stages)),
            "credential_reference_names": sorted(set(refs)),
            "findings": findings,
            "limitations": ["Static text heuristics, not a YAML/Groovy parser",
                            "Does not resolve includes, runtime secrets or shared libraries",
                            "Never evaluates pipeline code or reads secret values"]}

def main():
    parser = argparse.ArgumentParser(description="Read-only CI/CD file inspector")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps([analyze(p) for p in args.files], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
