"""Pinned integrity-only physical-completion corpus gate; no semantic or signer claims."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

PIN = "87eae0bddf217e242c1d85c25c6271c5725f819f"
MANIFEST_BLOB = "9505b39e35a8a12bd2d1cf6b8159e4ad2950cdd5"
CORPUS = "corpora/vectors-physical-completion"
UPSTREAM = "https://github.com/probityai/agent-evidence-vectors.git"
COUNTS = {"conformant": 17, "nonconformant": 17, "ambiguous": 14}

class AdmissionError(ValueError):
    pass

def strict_json(data):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise AdmissionError("duplicate JSON key")
            out[key] = value
        return out
    def refuse_number(token):
        raise AdmissionError("invalid JSON number: " + token)
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique, parse_constant=refuse_number)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AdmissionError("invalid JSON") from exc

def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + bytes([0]) + data).hexdigest()

def safe_record(root, name):
    if not isinstance(name, str) or not re.fullmatch(r"cases/[a-z0-9][a-z0-9-]*/record\.json", name):
        raise AdmissionError("unsafe record path")
    path = root
    for part in name.split("/"):
        path = path / part
        if path.is_symlink():
            raise AdmissionError("symlink in corpus")
    if not path.is_file():
        raise AdmissionError("missing record")
    return path.read_bytes()

def audit(root):
    manifest_path = root / "MANIFEST.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise AdmissionError("missing or symlinked manifest")
    raw = manifest_path.read_bytes()
    if git_blob_sha(raw) != MANIFEST_BLOB:
        raise AdmissionError("pinned manifest Git blob mismatch")
    m = strict_json(raw)
    if not isinstance(m, dict) or m.get("suite") != "physical-completion/v1" or m.get("synthetic") is not True:
        raise AdmissionError("wrong suite or synthetic flag")
    if m.get("provenance", {}).get("source") != "hippoley, issue 80":
        raise AdmissionError("unexpected source attribution")
    rows = m.get("vectors")
    if not isinstance(rows, list) or len(rows) != 48:
        raise AdmissionError("wrong case count")
    counts = dict.fromkeys(COUNTS, 0)
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise AdmissionError("bad vector")
        name = row.get("id")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or name in seen:
            raise AdmissionError("invalid or duplicate case ID")
        seen.add(name)
        if row.get("path") != "cases/" + name or set(row.get("files", {})) != {"record.json"}:
            raise AdmissionError("unexpected case layout")
        digest = row["files"]["record.json"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AdmissionError("invalid SHA-256")
        payload = safe_record(root, row["path"] + "/record.json")
        if hashlib.sha256(payload).hexdigest() != digest:
            raise AdmissionError("record SHA-256 mismatch: " + name)
        if not isinstance(strict_json(payload), dict):
            raise AdmissionError("record must be JSON object")
        decision = row.get("expected", {}).get("decision")
        if decision not in counts:
            raise AdmissionError("unknown decision")
        counts[decision] += 1
    if counts != COUNTS or m.get("counts") != COUNTS:
        raise AdmissionError("case counts differ")
    return {"release": "v0.39.0", "commit": PIN, "manifest_blob": MANIFEST_BLOB,
            "records_sha256_checked": 48, "counts": counts,
            "manifest_digest_recomputed": False, "publisher_signature_authenticated": False,
            "independent_semantic_parity": "NOT_EVALUATED", "physical_effect_verified": False}

def git(*args, cwd):
    p = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True,
                       check=True, timeout=180, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    return p.stdout.strip()

def run(destination, checkout=None):
    with tempfile.TemporaryDirectory(prefix="counterproof-v039-") as tmp:
        repo = checkout if checkout is not None else Path(tmp)
        if checkout is None:
            git("init", "--quiet", cwd=repo)
            git("remote", "add", "origin", UPSTREAM, cwd=repo)
            git("fetch", "--quiet", "--depth", "1", "origin", "refs/tags/v0.39.0", cwd=repo)
            if git("rev-parse", "FETCH_HEAD^{}", cwd=repo) != PIN:
                raise AdmissionError("tag target drift")
            git("checkout", "--quiet", "--detach", PIN, cwd=repo)
        if git("rev-parse", "HEAD", cwd=repo) != PIN:
            raise AdmissionError("wrong checkout commit")
        if git("rev-parse", f"HEAD:{CORPUS}/MANIFEST.json", cwd=repo) != MANIFEST_BLOB:
            raise AdmissionError("manifest tree binding failed")
        result = audit(repo / CORPUS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--receipt", type=Path, default=Path("admission.json"))
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.receipt, args.checkout), sort_keys=True))
    except (AdmissionError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        parser.exit(2, f"NOT ADMITTED: {exc}\n")
