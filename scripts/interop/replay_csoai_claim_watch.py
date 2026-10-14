"""Replay one pinned public CSOAI Measurement Capsule batch.

This script is intentionally small and network-agnostic: CI fetches the exact
commit-pinned gzip bytes, this script verifies the bytes and draft-level
identifier/root semantics.

It does not claim CSOAI or IETF endorsement.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
from pathlib import Path

from skill_factory.evolution.measurement_capsule_verify import verify_jsonl_batch


EXPECTED_GZIP_SHA256 = "70451eda2d8166b9a61084f5c01b8ff57210a7016d97ab0320b4c730f2b827ed"
EXPECTED_ROOT = "5e6440b6f9fbccdc2dca66aff3c79c02f649ccb56cd795d0f043b651dd50c32e"
EXPECTED_COUNT = 1


def replay(path: Path) -> None:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_GZIP_SHA256:
        raise SystemExit(
            f"gzip sha256 mismatch: got={digest} expected={EXPECTED_GZIP_SHA256}"
        )

    data = gzip.decompress(raw)
    lines = data.splitlines(keepends=True)
    result = verify_jsonl_batch(
        lines,
        expected_merkle_root=EXPECTED_ROOT,
        expected_n_capsules=EXPECTED_COUNT,
    )

    print("CSOAI claim_watch replay: PASS")
    print(f"capsules={result.n_capsules}")
    print(f"merkle_root={result.merkle_root}")
    print(f"capsule_id={result.capsule_ids[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("capsules_gz", type=Path)
    args = parser.parse_args()
    replay(args.capsules_gz)


if __name__ == "__main__":
    main()
