#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_SIGNATURE = {
    "CONTROL": (False, False, False),
    "BAD": (True, True, True),
    "REVERT": (False, False, False),
}


def _unit_active(snapshot: dict) -> bool:
    return "ActiveState=active" in snapshot["keyring_unit"]["stdout"]


def _pid_nonzero(snapshot: dict) -> bool:
    return "MainPID=0" not in snapshot["keyring_unit"]["stdout"]


def _portal_wants_keyring(snapshot: dict) -> bool:
    return "gnome-keyring-daemon.service" in snapshot["portal_dependencies"]["stdout"]


def _not_in_initialization(snapshot: dict) -> bool:
    return "NotInInitialization" in snapshot["keyring_journal"]["stdout"]


def summarize(snapshot: dict, image: str) -> dict:
    return {
        "image": image,
        "keyring_unit_active": _unit_active(snapshot),
        "keyring_pid_nonzero": _pid_nonzero(snapshot),
        "portal_wants_keyring": _portal_wants_keyring(snapshot),
        "not_in_initialization": _not_in_initialization(snapshot),
        "login_alias": snapshot["secret_login_alias"]["stdout"],
    }


def signature(row: dict) -> tuple[bool, bool, bool]:
    return (
        row["keyring_unit_active"],
        row["portal_wants_keyring"],
        row["not_in_initialization"],
    )


def _load_diagnostics(diagnostics_dir: Path) -> dict[str, tuple[Path, dict]]:
    by_image: dict[str, tuple[Path, dict]] = {}
    for path in sorted(diagnostics_dir.rglob("counterproof-keyring-diagnostic-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        image = data["image"]
        if image in by_image:
            raise ValueError(
                "AMBIGUOUS_EVIDENCE: multiple published diagnostics found "
                f"for image {image!r}"
            )
        by_image[image] = (path, data["snapshot"])
    return by_image


def _candidate_roles(
    *,
    control_image: str,
    bad_image: str,
    revert_image: str,
) -> dict[str, str]:
    roles = {
        "CONTROL": control_image,
        "BAD": bad_image,
        "REVERT": revert_image,
    }
    if len(set(roles.values())) != len(roles):
        raise ValueError(
            "INVALID_EXPERIMENT: CONTROL, BAD, and REVERT must reference distinct images"
        )
    return roles


def _require_published(
    by_image: dict[str, tuple[Path, dict]],
    roles: dict[str, str],
) -> None:
    missing = {role: image for role, image in roles.items() if image not in by_image}
    if missing:
        raise ValueError(
            "EVIDENCE_NOT_PUBLISHED: diagnostic computation may have run, "
            f"but no published artifact was found for {missing}"
        )


def build_receipt(
    diagnostics_dir: Path,
    *,
    control_image: str,
    bad_image: str,
    revert_image: str,
    oracle_revision: str,
) -> dict:
    roles = _candidate_roles(
        control_image=control_image,
        bad_image=bad_image,
        revert_image=revert_image,
    )
    by_image = _load_diagnostics(diagnostics_dir)
    _require_published(by_image, roles)

    candidates = {
        role: summarize(by_image[image][1], image)
        for role, image in roles.items()
    }

    observed = {role: signature(candidates[role]) for role in roles}
    witness = all(observed[role] == EXPECTED_SIGNATURE[role] for role in roles)

    return {
        "schema_version": 1,
        "case": "ublue-os/bluefin#4539",
        "experiment": "CONTROL -> + historical drop-in -> BAD -> remove drop-in -> REVERT",
        "oracle_revision": oracle_revision,
        "historical_image_status": "ORIGINAL_REGISTRY_ARTIFACTS_UNAVAILABLE",
        "verdict": (
            "WITNESSED_CONTROLLED_CAUSAL"
            if witness
            else "INCONCLUSIVE_CONTROLLED_CAUSAL"
        ),
        "candidates": candidates,
    }


def prepare_generic_replay(
    diagnostics_dir: Path,
    *,
    output_dir: Path,
    control_image: str,
    bad_image: str,
    revert_image: str,
    oracle_revision: str,
    adapter_revision: str,
) -> Path:
    """Normalize the Bluefin diagnostics into the generic causal-replay protocol."""
    roles = _candidate_roles(
        control_image=control_image,
        bad_image=bad_image,
        revert_image=revert_image,
    )
    by_image = _load_diagnostics(diagnostics_dir)
    _require_published(by_image, roles)

    output_dir.mkdir(parents=True, exist_ok=True)
    candidates: dict[str, dict[str, str]] = {}
    sources_dir = output_dir / "sources"
    sources_dir.mkdir(exist_ok=True)
    for role, image in roles.items():
        source_path, snapshot = by_image[image]
        evidence_name = f"{role.lower()}.json"
        source_name = f"sources/{role.lower()}-diagnostic.json"
        payload = {
            "candidate": image,
            "observation": summarize(snapshot, image),
        }
        (output_dir / evidence_name).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / source_name).write_bytes(source_path.read_bytes())
        candidates[role] = {
            "identity": image,
            "evidence": evidence_name,
            "source_evidence": source_name,
        }

    manifest = {
        "schema_version": 1,
        "case": "ublue-os/bluefin#4539-controlled-keyring-lifecycle",
        "experiment": (
            "CONTROL -> add historical portal/keyring ordering drop-in -> "
            "BAD -> remove drop-in -> REVERT"
        ),
        "oracle": {
            "id": "bluefin-gnome-qemu-keyring-lifecycle",
            "revision": oracle_revision,
            "adapter_revision": adapter_revision,
            "scope": "keyring service lifecycle / portal dependency, not keyring unlock",
        },
        "identity_path": "candidate",
        "observation_root": "observation",
        "candidates": candidates,
        "expectations": [
            {
                "path": "keyring_unit_active",
                "CONTROL": False,
                "BAD": True,
                "REVERT": False,
            },
            {
                "path": "keyring_pid_nonzero",
                "CONTROL": False,
                "BAD": True,
                "REVERT": False,
            },
            {
                "path": "portal_wants_keyring",
                "CONTROL": False,
                "BAD": True,
                "REVERT": False,
            },
            {
                "path": "not_in_initialization",
                "CONTROL": False,
                "BAD": True,
                "REVERT": False,
            },
            {
                "path": "login_alias",
                "CONTROL": "(objectpath '/',)",
                "BAD": "(objectpath '/',)",
                "REVERT": "(objectpath '/',)",
            },
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def render_markdown(receipt: dict) -> str:
    lines = [
        "## Bluefin #4539 controlled causal receipt",
        "",
        f"**Verdict: {receipt['verdict']}**",
        "",
        "| candidate | keyring unit active | portal→keyring dependency | NotInInitialization |",
        "|---|---:|---:|---:|",
    ]
    for role in ("CONTROL", "BAD", "REVERT"):
        row = receipt["candidates"][role]
        lines.append(
            f"| {role} | {row['keyring_unit_active']} | "
            f"{row['portal_wants_keyring']} | {row['not_in_initialization']} |"
        )
    lines += [
        "",
        "Historical GHCR artifacts are unavailable; this verdict is explicitly "
        "controlled-causal, not an original historical-image replay.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("diagnostics_dir", type=Path)
    parser.add_argument("--control-image", required=True)
    parser.add_argument("--bad-image", required=True)
    parser.add_argument("--revert-image", required=True)
    parser.add_argument("--oracle-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--generic-dir", type=Path)
    parser.add_argument("--adapter-revision")
    args = parser.parse_args()

    receipt = build_receipt(
        args.diagnostics_dir,
        control_image=args.control_image,
        bad_image=args.bad_image,
        revert_image=args.revert_image,
        oracle_revision=args.oracle_revision,
    )
    args.output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.summary:
        args.summary.write_text(render_markdown(receipt), encoding="utf-8")

    if args.generic_dir:
        if not args.adapter_revision:
            parser.error("--generic-dir requires --adapter-revision")
        manifest = prepare_generic_replay(
            args.diagnostics_dir,
            output_dir=args.generic_dir,
            control_image=args.control_image,
            bad_image=args.bad_image,
            revert_image=args.revert_image,
            oracle_revision=args.oracle_revision,
            adapter_revision=args.adapter_revision,
        )
        print(f"Generic causal replay manifest: {manifest}")

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["verdict"] == "WITNESSED_CONTROLLED_CAUSAL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
