# SPDX-FileCopyrightText: Contributors to openadr3-client-gac-compliance
# SPDX-License-Identifier: Apache-2.0
"""Apply a bounded candidate fix to installed ElaadNL 3.2.4 for CI.

This modifies only the runner's installed files, not upstream GitHub.
After validating, the exact changes can be proposed in a focused PR.
"""
from importlib import import_module
from pathlib import Path


for ver in ("gac20", "gac21", "gac22"):
    mod = import_module(f"openadr3_client_gac_compliance.{ver}.event_gac_compliant")
    file = Path(mod.__file__)
    source = file.read_text(encoding="utf-8")
    original = source

    needle = "        payload_descriptors = self.payload_descriptors[0]"
    replacement = (
        "        if not self.payload_descriptors:\n"
        "            return validation_errors\n\n"
        + needle
    )
    if source.count(needle) != 1:
        raise RuntimeError(f"{ver}: expected exactly one descriptor lookup")
    source = source.replace(needle, replacement, 1)

    if ver in ("gac21", "gac22"):
        fun = "def _event_interval_gac_compliant(self: Event)"
        start_fn = source.index(fun)
        body_start = source.index("        if len(interval.payloads) != 1:", start_fn)
        body_end = source.index("\n    return validation_errors", body_start)
        bad_block = source[body_start:body_end]
        # Indent payload checks underneath the for-loop, not outside it.
        fixed_block = "\n".join(
            "    " + line if line.strip() else line
            for line in bad_block.split("\n")
        )
        source = source[:body_start] + fixed_block + source[body_end:]

    if source == original:
        raise RuntimeError(f"{ver}: no changes made")
    compile(source, str(file), "exec")
    file.write_text(source, encoding="utf-8")
    print(f"Patched {ver}: {file}")
