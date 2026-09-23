"""Review and bind generated probe scaffolds to executable adapters."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def bind_probe_adapter(
    scaffold: dict[str, Any],
    *,
    adapter: tuple[str, ...],
    reviewed_by: str,
    review_note: str,
) -> dict[str, Any]:
    """Convert a reviewed draft probe scaffold into a ready experiment manifest."""
    if scaffold.get("status") != "draft":
        raise ValueError("probe scaffold must have status='draft' before binding")
    if not scaffold.get("review_required", False):
        raise ValueError("probe scaffold must require review before binding")
    if not adapter or not all(isinstance(part, str) and part.strip() for part in adapter):
        raise ValueError("adapter must contain one or more non-empty argv parts")
    if str(adapter[0]).startswith("TODO_"):
        raise ValueError("adapter placeholder cannot be bound as an executable adapter")
    if not reviewed_by.strip():
        raise ValueError("reviewed_by is required")
    if not review_note.strip():
        raise ValueError("review_note is required")

    cases = scaffold.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("probe scaffold requires one or more cases")

    bound = deepcopy(scaffold)
    bound["status"] = "ready"
    bound["review_required"] = False
    bound["adapter"] = list(adapter)
    bound["review"] = {
        "reviewed_by": reviewed_by.strip(),
        "note": review_note.strip(),
        "decision": "approved-for-execution",
    }

    notes = list(bound.get("notes", []))
    notes.append(
        "Adapter binding authorizes execution of the reviewed scaffold. "
        "It does not certify that the adapter implements the intended domain semantics."
    )
    bound["notes"] = notes
    return bound
